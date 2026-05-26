from sqlalchemy import text
from alerts_obj import Alerts


def test_mismatch_alert_sets_type(fresh_db):
    alert = Alerts("https://example.com/a.js", "old_hash", "new_hash")
    alert.missmatch_alert()
    assert alert.alert_type == "checksum"
    assert "Checksum mismatch" in alert.alert_msg
    assert "old_hash" in alert.alert_msg
    assert "new_hash" in alert.alert_msg


def test_new_script_alert_sets_type(fresh_db):
    alert = Alerts("https://example.com/new.js", None, None)
    alert.new_script_alert()
    assert alert.alert_type == "new_script"
    assert "New script detected" in alert.alert_msg


def test_save_to_db_persists_alert(fresh_db):
    from db.database import get_engine
    alert = Alerts("https://example.com/a.js", "old", "new")
    alert.missmatch_alert()
    alert.save_to_db()
    with get_engine().connect() as conn:
        rows = conn.execute(
            text("SELECT alert_type FROM alerts")
        ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "checksum"
