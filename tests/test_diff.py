from sqlalchemy import text
from db.database import get_engine


def _seed_alert_with_diff(javascript, alert_type, diff=None):
    with get_engine().connect() as conn:
        conn.execute(
            text("INSERT INTO alerts "
                 "(javascript, stored_checksum, new_checksum, date, alert_msg, alert_type, diff) "
                 "VALUES (:js, :stored, :new, :date, :msg, :type, :diff)"),
            {
                "js": javascript, "stored": "old_hash", "new": "new_hash",
                "date": "20260526_120000", "msg": "ALERT: test",
                "type": alert_type, "diff": diff,
            },
        )
        conn.commit()


def test_get_diff_returns_diff(client, auth_headers):
    _seed_alert_with_diff("https://example.com/a.js", "checksum",
                          diff="--- a\n+++ b\n@@ -1 +1 @@\n-old\n+new")
    alerts = client.get("/alerts", headers=auth_headers).json()
    alert_id = alerts[0]["id"]

    response = client.get(f"/alerts/{alert_id}/diff", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["alert_id"] == alert_id
    assert "old" in data["diff"]
    assert "new" in data["diff"]


def test_get_diff_no_diff_available(client, auth_headers):
    _seed_alert_with_diff("https://example.com/a.js", "new_script", diff=None)
    alerts = client.get("/alerts", headers=auth_headers).json()
    alert_id = alerts[0]["id"]

    response = client.get(f"/alerts/{alert_id}/diff", headers=auth_headers)
    assert response.status_code == 404


def test_get_diff_nonexistent_alert(client, auth_headers):
    response = client.get("/alerts/9999/diff", headers=auth_headers)
    assert response.status_code == 404


def test_diff_stored_via_alerts_obj(fresh_db):
    from alerts_obj import Alerts
    from db.database import get_engine
    a = Alerts("https://example.com/x.js", "old_hash", "new_hash",
                diff="--- a\n+++ b\n")
    a.missmatch_alert()
    a.save_to_db()
    with get_engine().connect() as conn:
        row = conn.execute(
            text("SELECT diff FROM alerts WHERE javascript='https://example.com/x.js'")
        ).fetchone()
    assert row[0] == "--- a\n+++ b\n"


def test_get_stored_javascript(fresh_db):
    from suricatajs_obj import SuricataJSObject
    obj = SuricataJSObject("https://example.com/a.js", "var x = 1;")
    obj.save_to_db()
    stored = obj.get_stored_javascript()
    assert stored == "var x = 1;"


def test_get_stored_javascript_missing(fresh_db):
    from suricatajs_obj import SuricataJSObject
    obj = SuricataJSObject("https://example.com/missing.js", "var x = 1;")
    stored = obj.get_stored_javascript()
    assert stored == ""
