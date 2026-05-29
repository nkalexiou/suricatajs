# suricatajs

**JavaScript integrity monitoring** — detect unauthorized script changes before they become incidents.

suricatajs continuously scans your web properties, fingerprints every JavaScript file and inline script it finds, and alerts you the moment anything changes or something new appears. It was built to catch web-skimming (Magecart-style) attacks and supply-chain compromises early.

---

## Features

- **Checksum-based change detection** — SHA-256 fingerprints for every external and inline script
- **New script detection** — alerts when a script appears for the first time
- **CDN-aware attribution** — scripts are associated with the page that loaded them, not the CDN they were served from
- **Browser-mode scanning** — Playwright option for JS-heavy SPAs that load scripts dynamically
- **SRI hash generation** — sha384 SRI hash included in every alert for Content Security Policy use
- **Diff view** — unified diff for checksum-mismatch alerts
- **Web UI** — full management interface: domains, target URLs, detection log, alert triage
- **Auto-scan** — new URLs are scanned immediately after being added; interval scanning runs in the background
- **Two-action alert triage** — *Dismiss & Approve* updates the baseline (expected change); *Resolve* closes the incident without updating the baseline
- **Role-based access** — `admin` (user management) and `operator` (everything else)
- **Webhooks** — POST alert payloads to any endpoint on detection
- **Prometheus metrics** — `/metrics` endpoint for Grafana/alerting integration
- **PostgreSQL or SQLite** — SQLite for local dev, Postgres for production
- **Docker-first** — single-container image, multi-stage build (Node → Python)

---

## Quick start with Docker Compose

```bash
# Copy the example env file and set your secrets
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD and JWT_SECRET at minimum

docker compose up -d
```

On first start the admin password is printed once to the logs:

```bash
docker compose logs api | grep "Admin password"
```

Open `http://localhost:8085` and log in with `admin@localhost` and that password. Change it immediately under **Profile**.

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./db/surikatajs.db` | SQLite or PostgreSQL connection string |
| `JWT_SECRET` | *(random at startup)* | HMAC-SHA256 signing secret for session cookies. Set this or sessions expire on restart. |
| `JWT_EXPIRE_MINUTES` | `480` | Session lifetime in minutes |
| `API_KEYS` | *(empty)* | Comma-separated keys accepted in `X-API-Key` header (used by the scanner and external integrations) |
| `SCAN_INTERVAL_MINUTES` | `60` | Default interval between rescans when no per-target interval is set |
| `POSTGRES_PASSWORD` | `suricatajs` | Password for the Postgres service in Docker Compose |
| `API_PORT` | `8085` | Host port the API is exposed on |
| `SCAN_MODE` | `once` | Standalone runner mode: `once` (single pass) or `scheduled` (APScheduler loop) |

Create a `.env` file at the repo root — Docker Compose picks it up automatically:

```env
POSTGRES_PASSWORD=change_me
JWT_SECRET=change_me_to_a_long_random_string
API_KEYS=your_scanner_key
```

---

## Architecture

```
suricatajs/
├── api/                   FastAPI application
│   ├── main.py            App factory, lifespan, SPA middleware, interval scheduler
│   ├── auth.py            JWT cookie + X-API-Key auth dependencies
│   ├── models.py          Pydantic request/response models
│   └── routers/           alerts, auth, domains, health, metrics, targets, users
│
├── scanner/               Scanning engine
│   ├── engine.py          Core logic: fetch page, fingerprint scripts, write alerts
│   ├── discovery.py       Crawl-depth URL discovery
│   ├── loader.py          Load targets from DB (or targets.txt fallback)
│   ├── playwright_scanner.py  Browser-mode script extraction
│   └── scheduler.py       Standalone APScheduler wrapper (used by run.py)
│
├── db/
│   └── database.py        SQLAlchemy engine, schema init, incremental migrations
│
├── alerts_obj.py          Alert model — construct, save to DB, deliver webhook
├── suricatajs_obj.py      Script baseline model — compare and store checksums
├── webhooks/              Webhook delivery with retry/backoff
├── run.py                 Standalone CLI entry point
│
└── ui/                    React + TypeScript SPA (Vite, Tailwind, shadcn/ui)
    └── src/
        ├── pages/         Login, Domains, DomainDetail, Alerts, Metrics, Profile, Users
        ├── components/    UrlAccordion, ScriptsTable, Sidebar, …
        └── api/           TanStack Query hooks for every backend resource
```

**Auth model**

- The web UI authenticates via an httpOnly `session` cookie (JWT, HS256).
- The scanner and external tools authenticate via `X-API-Key` header.
- Both paths are accepted on all protected endpoints — they coexist without conflict.

---

## Running locally (development)

### Backend

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start the API (auto-reloads)
uvicorn api.main:app --reload --port 8085
```

### Frontend

```bash
cd ui
npm install
npm run dev          # Vite dev server on :5173, proxies API calls to :8085
```

### Scanner (one-shot)

```bash
# Scan all targets in the DB once
python run.py
```

---

## Running with Docker (single container)

```bash
docker build -t suricatajs .
docker run -p 8085:8085 \
  -e JWT_SECRET=your_secret \
  -e API_KEYS=your_key \
  suricatajs
```

The UI is served from the same container on port 8085.

---

## Scanning modes

| Mode | How to use |
|---|---|
| **UI-triggered** | Add a URL in the web UI — a scan fires immediately in the background |
| **Interval** | The API process runs a background scheduler; every target is rescanned on its configured interval (default `SCAN_INTERVAL_MINUTES`) |
| **Standalone once** | `python run.py` — one full pass over all targets, then exits |
| **Standalone scheduled** | `SCAN_MODE=scheduled python run.py` — blocking APScheduler loop |

---

## Alert types

| Type | Meaning | Dismiss & Approve | Resolve |
|---|---|---|---|
| `new_script` | A script appeared that was not in the baseline | Accepts it as the new baseline | Closes the alert; baseline unchanged |
| `checksum` | A tracked script's content changed | Updates baseline to the new hash | Closes the alert; baseline unchanged |

---

## Tests

```bash
./venv/bin/pytest tests/ -q
```

---

## License

[MIT](LICENSE)
