# tests/test_schema.py
from sqlalchemy import text
from db.database import get_engine


def test_alerts_has_id_column(fresh_db):
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("INSERT INTO alerts (javascript, stored_checksum, new_checksum, date, alert_msg, alert_type) VALUES ('x', 'a', 'b', '20260526_120000', 'msg', 'checksum')"))
        conn.commit()
        result = conn.execute(text("SELECT id FROM alerts LIMIT 1")).fetchone()
    assert result is not None
    assert result[0] is not None


def test_alerts_has_diff_column(fresh_db):
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("INSERT INTO alerts (javascript, stored_checksum, new_checksum, date, alert_msg, alert_type, diff) VALUES ('x', 'a', 'b', '20260526_120000', 'msg', 'checksum', 'my diff')"))
        conn.commit()
        result = conn.execute(text("SELECT diff FROM alerts WHERE javascript='x'")).fetchone()
    assert result[0] == "my diff"


def test_targets_table_exists(fresh_db):
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text(
            "INSERT INTO targets (url, name, created_at) VALUES ('https://example.com', 'Test', '20260526_120000')"
        ))
        conn.commit()
        result = conn.execute(text("SELECT id, url, name, tags, owner, scan_interval_minutes, approved_checksum, approval_note, approved_at, created_at FROM targets LIMIT 1")).fetchone()
    assert result[1] == "https://example.com"
