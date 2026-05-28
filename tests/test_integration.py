import os
import pytest

JUICE_SHOP = "https://juice-shop.herokuapp.com/"

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "1",
    reason="Set RUN_INTEGRATION_TESTS=1 to run live tests",
)


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


def test_first_scan_creates_new_script_alerts(isolated_db):
    from run import check_target
    check_target({"url": JUICE_SHOP})

    from db.database import get_engine
    from sqlalchemy import text
    engine = get_engine()
    with engine.connect() as conn:
        alerts = conn.execute(text("SELECT alert_type, javascript FROM alerts")).fetchall()

    assert len(alerts) > 0
    types = {a[0] for a in alerts}
    assert "new_script" in types


def test_second_scan_no_new_alerts(isolated_db):
    from run import check_target
    check_target({"url": JUICE_SHOP})

    from db.database import get_engine
    from sqlalchemy import text
    engine = get_engine()
    with engine.connect() as conn:
        count_after_first = conn.execute(text("SELECT COUNT(*) FROM alerts")).fetchone()[0]

    check_target({"url": JUICE_SHOP})

    with engine.connect() as conn:
        count_after_second = conn.execute(text("SELECT COUNT(*) FROM alerts")).fetchone()[0]

    assert count_after_second == count_after_first


def test_alerts_have_id_and_correct_schema(isolated_db):
    from run import check_target
    check_target({"url": JUICE_SHOP})

    from db.database import get_engine
    from sqlalchemy import text
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT id, javascript, stored_checksum, new_checksum, date, alert_msg, alert_type, diff "
                 "FROM alerts")
        ).fetchall()

    assert len(rows) > 0
    for row in rows:
        assert row[0] is not None        # id auto-assigned
        assert row[1] is not None        # javascript URL or inline synthetic URL
        assert row[4] is not None        # date


def test_api_returns_alerts_after_scan(isolated_db):
    from run import check_target
    check_target({"url": JUICE_SHOP})

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


def test_inline_scripts_detected(isolated_db):
    from run import check_target
    check_target({"url": JUICE_SHOP})

    from db.database import get_engine
    from sqlalchemy import text
    engine = get_engine()
    with engine.connect() as conn:
        inline_alerts = conn.execute(
            text("SELECT javascript FROM alerts WHERE javascript LIKE '%#inline-%'")
        ).fetchall()

    for row in inline_alerts:
        assert "#inline-" in row[0]
        hex_part = row[0].split("#inline-")[1]
        assert len(hex_part) == 16
        assert all(c in "0123456789abcdef" for c in hex_part)


def test_targets_loaded_from_txt_file(isolated_db, tmp_path):
    from scanner.loader import load_targets
    from db.database import get_engine
    from sqlalchemy import text

    targets_file = tmp_path / "targets.txt"
    targets_file.write_text(f"{JUICE_SHOP}\n")

    targets = load_targets(str(targets_file))

    assert len(targets) > 0
    assert targets[0]["url"] == JUICE_SHOP

    engine = get_engine()
    with engine.connect() as conn:
        db_targets = conn.execute(text("SELECT url FROM targets")).fetchall()
    assert db_targets[0][0] == JUICE_SHOP


def test_yaml_targets_file(isolated_db, tmp_path):
    from scanner.loader import load_targets

    yaml_file = tmp_path / "targets.yaml"
    yaml_file.write_text(f"""
targets:
  - url: {JUICE_SHOP}
    name: Juice Shop
    tags:
      - demo
    scan_interval_minutes: 5
""")
    targets = load_targets(str(yaml_file))
    assert len(targets) == 1
    assert targets[0]["name"] == "Juice Shop"
    assert targets[0]["tags"] == ["demo"]
    assert targets[0]["scan_interval_minutes"] == 5


def test_crawl_depth_1_discovers_subpages(isolated_db):
    from scanner.discovery import discover_urls

    pages = discover_urls(JUICE_SHOP, max_depth=1)
    assert len(pages) >= 1
    assert pages[0] == JUICE_SHOP


def test_check_target_with_crawl_depth_1_creates_alerts(isolated_db):
    from run import check_target
    check_target({"url": JUICE_SHOP, "crawl_depth": 1, "use_playwright": False})

    from db.database import get_engine
    from sqlalchemy import text
    with get_engine().connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM alerts")).fetchone()[0]
    assert count > 0


def test_check_target_with_playwright_creates_alerts(isolated_db):
    from run import check_target
    check_target({"url": JUICE_SHOP, "crawl_depth": 0, "use_playwright": True})

    from db.database import get_engine
    from sqlalchemy import text
    with get_engine().connect() as conn:
        alerts = conn.execute(text("SELECT alert_type, javascript FROM alerts")).fetchall()

    assert len(alerts) > 0
    types = {a[0] for a in alerts}
    assert "new_script" in types
