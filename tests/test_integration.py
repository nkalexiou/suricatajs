import http.server
import os
import threading

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "1",
    reason="Set RUN_INTEGRATION_TESTS=1 to run integration tests",
)

# Static pages served by the local test server
_INDEX_HTML = (
    b"<html><body>"
    b'<script src="/app.js"></script>'
    b"<script>console.log('inline-test');</script>"
    b'<a href="/shop">Shop</a>'
    b"</body></html>"
)
_APP_JS = b"var appVersion = '1.0';"
_SHOP_HTML = b"<html><body><script src='/shop.js'></script></body></html>"
_SHOP_JS = b"var shopLoaded = true;"

_RESPONSES = {
    "/": (200, "text/html", _INDEX_HTML),
    "/app.js": (200, "application/javascript", _APP_JS),
    "/shop": (200, "text/html", _SHOP_HTML),
    "/shop.js": (200, "application/javascript", _SHOP_JS),
}


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        entry = _RESPONSES.get(self.path)
        if entry:
            status, content_type, body = entry
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def local_server():
    server = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("API_KEYS", "test-key")
    from db.database import reset_engine, init_db
    reset_engine()
    init_db()
    yield
    reset_engine()


def test_first_scan_creates_new_script_alerts(isolated_db, local_server):
    from scanner.engine import check_target
    check_target({"url": local_server + "/"})

    from db.database import get_engine
    from sqlalchemy import text
    with get_engine().connect() as conn:
        alerts = conn.execute(text("SELECT alert_type, javascript FROM alerts")).fetchall()

    assert len(alerts) > 0
    types = {a[0] for a in alerts}
    assert "new_script" in types


def test_second_scan_no_new_alerts(isolated_db, local_server):
    from scanner.engine import check_target
    url = local_server + "/"
    check_target({"url": url})

    from db.database import get_engine
    from sqlalchemy import text
    engine = get_engine()
    with engine.connect() as conn:
        count_after_first = conn.execute(text("SELECT COUNT(*) FROM alerts")).fetchone()[0]

    check_target({"url": url})

    with engine.connect() as conn:
        count_after_second = conn.execute(text("SELECT COUNT(*) FROM alerts")).fetchone()[0]

    assert count_after_second == count_after_first


def test_alerts_have_id_and_correct_schema(isolated_db, local_server):
    from scanner.engine import check_target
    check_target({"url": local_server + "/"})

    from db.database import get_engine
    from sqlalchemy import text
    with get_engine().connect() as conn:
        rows = conn.execute(
            text("SELECT id, javascript, stored_checksum, new_checksum, date, alert_msg, alert_type, diff "
                 "FROM alerts")
        ).fetchall()

    assert len(rows) > 0
    for row in rows:
        assert row[0] is not None   # id auto-assigned
        assert row[1] is not None   # javascript URL or inline synthetic URL
        assert row[4] is not None   # date


def test_api_returns_alerts_after_scan(isolated_db, local_server):
    from scanner.engine import check_target
    check_target({"url": local_server + "/"})

    from fastapi.testclient import TestClient
    from api.main import create_app
    client = TestClient(create_app())
    response = client.get("/alerts", headers={"X-API-Key": "test-key"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    alert = data[0]
    assert "id" in alert
    assert "javascript" in alert
    assert "alert_type" in alert
    assert "diff" in alert


def test_inline_scripts_detected(isolated_db, local_server):
    from scanner.engine import check_target
    check_target({"url": local_server + "/"})

    from db.database import get_engine
    from sqlalchemy import text
    with get_engine().connect() as conn:
        inline_alerts = conn.execute(
            text("SELECT javascript FROM alerts WHERE javascript LIKE '%#inline-%'")
        ).fetchall()

    assert len(inline_alerts) > 0
    for row in inline_alerts:
        assert "#inline-" in row[0]
        hex_part = row[0].split("#inline-")[1]
        assert len(hex_part) == 16
        assert all(c in "0123456789abcdef" for c in hex_part)


def test_targets_loaded_from_txt_file(isolated_db, local_server, tmp_path):
    from scanner.loader import load_targets
    from db.database import get_engine
    from sqlalchemy import text

    url = local_server + "/"
    targets_file = tmp_path / "targets.txt"
    targets_file.write_text(f"{url}\n")

    targets = load_targets(str(targets_file))

    assert len(targets) > 0
    assert targets[0]["url"] == url

    with get_engine().connect() as conn:
        db_targets = conn.execute(text("SELECT url FROM targets")).fetchall()
    assert db_targets[0][0] == url


def test_yaml_targets_file(isolated_db, local_server, tmp_path):
    from scanner.loader import load_targets

    url = local_server + "/"
    yaml_file = tmp_path / "targets.yaml"
    yaml_file.write_text(f"""
targets:
  - url: {url}
    name: Test Site
    tags:
      - demo
    scan_interval_minutes: 5
""")
    targets = load_targets(str(yaml_file))
    assert len(targets) == 1
    assert targets[0]["name"] == "Test Site"
    assert targets[0]["tags"] == ["demo"]
    assert targets[0]["scan_interval_minutes"] == 5


def test_crawl_depth_1_discovers_subpages(isolated_db, local_server):
    from scanner.discovery import discover_urls

    pages = discover_urls(local_server + "/", max_depth=1)
    urls = set(pages)
    assert local_server + "/" in urls
    assert local_server + "/shop" in urls


def test_check_target_with_crawl_depth_1_creates_alerts(isolated_db, local_server):
    from scanner.engine import check_target
    check_target({"url": local_server + "/", "crawl_depth": 1, "use_playwright": False})

    from db.database import get_engine
    from sqlalchemy import text
    with get_engine().connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM alerts")).fetchone()[0]
    assert count > 0


def test_check_target_with_playwright_creates_alerts(isolated_db, local_server):
    from scanner.engine import check_target
    check_target({"url": local_server + "/", "crawl_depth": 0, "use_playwright": True})

    from db.database import get_engine
    from sqlalchemy import text
    with get_engine().connect() as conn:
        alerts = conn.execute(text("SELECT alert_type, javascript FROM alerts")).fetchall()

    assert len(alerts) > 0
    types = {a[0] for a in alerts}
    assert "new_script" in types


def test_metrics_endpoint_accessible(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "suricatajs_scripts_total" in response.text


def test_scan_produces_sri_in_alerts(isolated_db, local_server):
    from scanner.engine import check_target
    check_target({"url": local_server + "/"})

    from db.database import get_engine
    from sqlalchemy import text
    with get_engine().connect() as conn:
        rows = conn.execute(text("SELECT sri FROM alerts")).fetchall()

    assert len(rows) > 0
    for row in rows:
        assert row[0] is not None
        assert row[0].startswith("sha384-")


def test_webhook_fires_on_scan(isolated_db, local_server, monkeypatch):
    monkeypatch.setenv("WEBHOOK_URL", "https://hooks.example.com/notify")
    from unittest.mock import patch, MagicMock
    ok_resp = MagicMock(status_code=200)
    ok_resp.raise_for_status.return_value = None

    with patch("webhooks.delivery.requests.post", return_value=ok_resp) as mock_post:
        from scanner.engine import check_target
        check_target({"url": local_server + "/"})

    assert mock_post.call_count > 0
    payload = mock_post.call_args_list[0][1]["json"]
    assert "alert_type" in payload
    assert "javascript" in payload
    assert "sri" in payload
