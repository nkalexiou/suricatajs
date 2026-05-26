"""
Integration tests against the live juice-shop instance.
Run with: RUN_INTEGRATION_TESTS=1 pytest tests/test_integration.py -v -s
These tests make real HTTP requests and write to a temp file-based SQLite DB.
"""
import os
import pytest
from sqlalchemy import text

JUICE_SHOP = "https://juice-shop.herokuapp.com/"

pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_INTEGRATION_TESTS"),
    reason="Set RUN_INTEGRATION_TESTS=1 to run integration tests",
)


@pytest.fixture(autouse=True)
def live_db(tmp_path, monkeypatch):
    """Use a temp file-based SQLite DB so integration tests are isolated."""
    db_path = tmp_path / "integration_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    from db.database import reset_engine, init_db
    reset_engine()
    init_db()
    yield
    reset_engine()


def test_first_scan_creates_new_script_alerts(tmp_path):
    """Scanning juice-shop for the first time should produce new_script alerts."""
    targets = tmp_path / "targets.txt"
    targets.write_text(JUICE_SHOP + "\n")

    from run import check
    check(targets_file=str(targets))

    from db.database import get_engine
    with get_engine().connect() as conn:
        row = conn.execute(
            text("SELECT COUNT(*) FROM alerts WHERE alert_type='new_script'")
        ).fetchone()
    assert row[0] > 0, "Expected at least one new_script alert after first scan"


def test_second_scan_produces_no_new_alerts(tmp_path):
    """Scanning juice-shop twice should produce no additional alerts on the second run."""
    targets = tmp_path / "targets.txt"
    targets.write_text(JUICE_SHOP + "\n")

    from run import check
    from db.database import get_engine

    check(targets_file=str(targets))
    with get_engine().connect() as conn:
        count_after_first = conn.execute(text("SELECT COUNT(*) FROM alerts")).fetchone()[0]

    assert count_after_first > 0, "First scan should create alerts"

    check(targets_file=str(targets))
    with get_engine().connect() as conn:
        count_after_second = conn.execute(text("SELECT COUNT(*) FROM alerts")).fetchone()[0]

    assert count_after_second == count_after_first, (
        f"Second scan should not create new alerts. "
        f"Before: {count_after_first}, After: {count_after_second}"
    )


def test_api_returns_alerts_after_scan(tmp_path, monkeypatch):
    """After a scan, the /alerts API endpoint should return the created alerts."""
    targets = tmp_path / "targets.txt"
    targets.write_text(JUICE_SHOP + "\n")

    monkeypatch.setenv("API_KEYS", "integration-test-key")

    from run import check
    check(targets_file=str(targets))

    from fastapi.testclient import TestClient
    from api.main import app

    client = TestClient(app)
    response = client.get("/alerts", headers={"X-API-Key": "integration-test-key"})
    assert response.status_code == 200
    alerts = response.json()
    assert len(alerts) > 0
    assert all(a["alert_type"] == "new_script" for a in alerts)
    assert all("juice-shop.herokuapp.com" in a["javascript"] for a in alerts)
