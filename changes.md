# suricatajs — Project Context for UI Development

This document captures the complete state of the backend after four implementation plans, to give a fresh session full context before building the UI.

---

## What is suricatajs

A self-hosted JavaScript integrity monitoring service. It detects Magecart/skimming attacks by:
1. Fetching web pages and extracting their `<script>` tags (external + inline)
2. Checksumming each script's content
3. Alerting when a script changes (checksum mismatch) or a new script appears
4. Storing all alerts, scripts, and targets in SQLite or PostgreSQL

---

## Repository layout

```
suricatajs/
├── run.py                        # Scanner entry point + core scan logic
├── alerts_obj.py                 # Alerts model (save to DB, to_dict, alert types)
├── suricatajs_obj.py             # SuricataJSObject (checksum, compare, save)
├── targets.txt                   # Legacy plain-text target list (URL per line)
│
├── api/
│   ├── main.py                   # FastAPI app factory + lifespan (calls init_db)
│   ├── auth.py                   # API key auth (X-API-Key header, fail-closed)
│   ├── models.py                 # Pydantic models (see below)
│   └── routers/
│       ├── alerts.py             # GET /alerts, GET /alerts/{id}/diff
│       ├── targets.py            # CRUD /targets + /targets/{id}/approve
│       ├── health.py             # GET /health
│       └── metrics.py            # GET /metrics (Prometheus, no auth)
│
├── db/
│   └── database.py               # Engine, init_db(), _migrate_db(), get_connection()
│
├── scanner/
│   ├── loader.py                 # load_targets() — DB-first, YAML/txt fallback
│   ├── scheduler.py              # APScheduler BlockingScheduler
│   ├── discovery.py              # discover_urls(seed, max_depth) — BFS crawler
│   └── playwright_scanner.py     # get_page_scripts(url) — headless Chromium
│
├── webhooks/
│   └── delivery.py               # deliver_webhook(payload) — POST with retry/backoff
│
└── tests/                        # 91 unit tests + 13 integration tests
```

---

## API reference

All endpoints except `/health` and `/metrics` require `X-API-Key` header. Configured via `API_KEYS` env var (comma-separated). If `API_KEYS` is unset, all requests return 401.

### Targets

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/targets` | List all targets |
| `POST` | `/targets` | Create a target |
| `DELETE` | `/targets/{id}` | Delete a target |
| `POST` | `/targets/{id}/approve` | Approve current scripts as baseline |

**Target fields (TargetCreate / TargetResponse):**
```json
{
  "id": 1,
  "url": "https://example.com/",
  "name": "Example",
  "tags": ["ecommerce"],
  "owner": "ops",
  "scan_interval_minutes": 30,
  "crawl_depth": 0,
  "use_playwright": false,
  "approved_checksum": null,
  "approval_note": null,
  "approved_at": null,
  "created_at": "20260528_120000"
}
```

`crawl_depth` — BFS depth for discovering subpages (0 = only the seed URL).  
`use_playwright` — use headless Chromium instead of requests+BeautifulSoup (for SPAs).

### Alerts

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/alerts` | List alerts; filters: `?type=`, `?javascript=`, `?date=` |
| `GET` | `/alerts/{id}/diff` | Get unified diff for a checksum-mismatch alert |

**Alert fields (AlertResponse):**
```json
{
  "id": 1,
  "javascript": "https://cdn.example.com/app.js",
  "stored_checksum": "sha256...",
  "new_checksum": "sha256...",
  "date": "20260528_120000",
  "alert_msg": "ALERT: Checksum mismatch ...",
  "alert_type": "checksum",
  "diff": "--- stored\n+++ current\n...",
  "sri": "sha384-abc123..."
}
```

`alert_type` values: `new_script` (first time seen), `checksum` (content changed).  
`sri` — SHA-384 SRI hash of the current script content (`sha384-<base64>`), ready to use in `<script integrity="...">`.  
`diff` — non-null only for `checksum` alerts.

### Metrics (no auth)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/metrics` | Prometheus text format |

Exposes: `suricatajs_alerts_total{alert_type}`, `suricatajs_scripts_total`, `suricatajs_targets_total`, `suricatajs_last_scan_timestamp_seconds`.

### Health (no auth)

`GET /health` → `{"status": "ok"}`

---

## Database schema

SQLite (default) or PostgreSQL. All migrations handled by `init_db()` + `_migrate_db()` in `db/database.py`.

```sql
-- Monitored scripts and their content/checksums
CREATE TABLE suricatajs (
    uri TEXT,
    javascript TEXT,    -- full JS source
    checksum TEXT,      -- SHA-256 of content
    date TEXT           -- YYYYMMDD_HHMMSS
);

-- Security alerts
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY,
    javascript TEXT,        -- URL or inline synthetic URL (page#inline-<sha256[:16]>)
    stored_checksum TEXT,   -- previous SHA-256 (null for new_script)
    new_checksum TEXT,      -- current SHA-256 (null for new_script)
    date TEXT,
    alert_msg TEXT,
    alert_type TEXT,        -- 'new_script' | 'checksum'
    diff TEXT,              -- unified diff (null unless checksum mismatch)
    sri TEXT                -- sha384-<base64> of current content
);

-- Scan targets
CREATE TABLE targets (
    id INTEGER PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    name TEXT,
    tags TEXT,              -- JSON array stored as string
    owner TEXT,
    scan_interval_minutes INTEGER,
    approved_checksum TEXT,
    approval_note TEXT,
    approved_at TEXT,
    created_at TEXT NOT NULL,
    crawl_depth INTEGER NOT NULL DEFAULT 0,
    use_playwright INTEGER NOT NULL DEFAULT 0
);
```

---

## Scanner behaviour

**Entry point:** `python run.py`

**Environment variables:**
| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./db/surikatajs.db` | SQLAlchemy DB URL |
| `API_KEYS` | (unset → all requests rejected) | Comma-separated API keys |
| `SCAN_MODE` | `once` | `once` or `scheduled` |
| `SCAN_INTERVAL_MINUTES` | `60` | Used when `SCAN_MODE=scheduled` |
| `WEBHOOK_URL` | (unset → webhooks disabled) | POST target for alert payloads |

**Scan flow per target:**
1. If `crawl_depth > 0`: BFS-discover same-domain subpages via `scanner/discovery.py`
2. For each page: fetch with requests+BS4 (default) or Playwright (`use_playwright=True`)
3. For each external `<script src>`: checksum, compare with DB, alert if changed or new
4. For each inline `<script>`: same, using synthetic URL `{page_url}#inline-{sha256[:16]}`
5. New/changed alerts trigger `deliver_webhook()` if `WEBHOOK_URL` is set

**Per-target scan intervals** (scheduler mode): each target uses its own `scan_interval_minutes` if set, otherwise the global `SCAN_INTERVAL_MINUTES`.

---

## Dev setup

```bash
python -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/playwright install chromium

# Run unit tests
venv/bin/pytest tests/ --ignore=tests/test_integration.py -v

# Run integration tests (local HTTP server, no external deps)
RUN_INTEGRATION_TESTS=1 venv/bin/pytest tests/test_integration.py -v

# Start API server
export DATABASE_URL=sqlite:///./db/dev.db
export API_KEYS=mykey
venv/bin/uvicorn api.main:app --reload --port 8085
```

---

## What was implemented (plans 1–4)

**Plan 1 — Foundation**
- FastAPI app with lifespan (`init_db()` on startup)
- SQLAlchemy 2.0 Core (no ORM), SQLite + PostgreSQL support
- Auth middleware: `X-API-Key` header, fail-closed (generic 401 when `API_KEYS` unset)
- `GET /health`, `GET /alerts` with filters, `GET /alerts/{id}/diff`
- DB migration system (`_migrate_db()`) for zero-downtime upgrades

**Plan 2 — Scanner Core**
- APScheduler-based scheduled scanning (`SCAN_MODE=scheduled`)
- Target CRUD API (`/targets`) with YAML and plain-text file import
- JS diff generation for mismatch alerts (unified diff stored in DB)
- `POST /targets/{id}/approve` baseline approval workflow
- Per-target `scan_interval_minutes` overrides global interval
- Inline script monitoring with synthetic URL (`#inline-<sha256[:16]>`)

**Plan 3 — Advanced Scanning**
- `scanner/discovery.py`: BFS auto-discovery of same-domain subpages
- `scanner/playwright_scanner.py`: headless Chromium for SPA/dynamic scripts
- Per-target `crawl_depth` and `use_playwright` fields (DB + API)
- `check_target()` refactored to dispatch to requests or Playwright per page

**Plan 4 — Integrations**
- `GET /metrics`: Prometheus endpoint (no auth) with 4 metrics
- SRI hash (`sha384-...`) computed at scan time, stored in alerts table, returned in API
- `webhooks/delivery.py`: POST alert payload to `WEBHOOK_URL` with 3-attempt exponential backoff (1s, 2s)

---

## Next task: UI

Build a web UI for this API. The user will define scope, but the natural starting points are:
- **Alerts dashboard**: list alerts, filter by type/date/URL, show diff inline
- **Targets management**: create/edit/delete targets, configure crawl_depth and use_playwright
- **Metrics/status**: last scan time, alert counts, targets overview

The API base URL in dev is `http://localhost:8085`. Authentication is via `X-API-Key` header. The API has full CORS support needed for a browser-based UI (not yet added — will likely be needed).

CORS is **not yet configured** on the FastAPI app. This will need to be added before a browser-based UI can call the API.
