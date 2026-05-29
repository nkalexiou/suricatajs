# tests/test_inline.py
import hashlib
from sqlalchemy import text
from db.database import get_engine


def test_inline_script_creates_new_script_alert(fresh_db):
    from run import _scan_inline_script
    _scan_inline_script("https://example.com/", "var x = 1;")

    with get_engine().connect() as conn:
        alerts = conn.execute(text("SELECT javascript, alert_type FROM alerts")).fetchall()
        scripts = conn.execute(text("SELECT uri FROM suricatajs")).fetchall()

    assert len(alerts) == 1
    assert alerts[0][1] == "new_script"
    script_id = hashlib.sha256("var x = 1;".encode()).hexdigest()[:16]
    expected_url = f"https://example.com/#inline-{script_id}"
    assert alerts[0][0] == expected_url
    assert scripts[0][0] == expected_url


def test_inline_script_same_content_no_duplicate_alert(fresh_db):
    from run import _scan_inline_script
    _scan_inline_script("https://example.com/", "var x = 1;")
    _scan_inline_script("https://example.com/", "var x = 1;")

    with get_engine().connect() as conn:
        alerts = conn.execute(text("SELECT id FROM alerts")).fetchall()

    assert len(alerts) == 1


def test_inline_script_changed_content_treated_as_new_script(fresh_db):
    from run import _scan_inline_script
    _scan_inline_script("https://example.com/", "var x = 1;")
    _scan_inline_script("https://example.com/", "var x = 2;")

    with get_engine().connect() as conn:
        alerts = conn.execute(text("SELECT alert_type FROM alerts ORDER BY rowid")).fetchall()

    assert len(alerts) == 2
    assert all(a[0] == "new_script" for a in alerts)


def test_inline_script_empty_content_skipped(fresh_db):
    from run import _scan_inline_script
    _scan_inline_script("https://example.com/", "   ")

    with get_engine().connect() as conn:
        alerts = conn.execute(text("SELECT id FROM alerts")).fetchall()

    assert len(alerts) == 0


def test_inline_script_whitespace_stripped_before_hashing(fresh_db):
    from run import _scan_inline_script
    _scan_inline_script("https://example.com/", "  var x = 1;  ")
    _scan_inline_script("https://example.com/", "var x = 1;")

    with get_engine().connect() as conn:
        alerts = conn.execute(text("SELECT id FROM alerts")).fetchall()

    assert len(alerts) == 1


def test_inline_script_synthetic_url_format(fresh_db):
    from run import _scan_inline_script
    _scan_inline_script("https://example.com/page", "alert(1)")

    with get_engine().connect() as conn:
        scripts = conn.execute(text("SELECT uri FROM suricatajs")).fetchall()

    uri = scripts[0][0]
    assert uri.startswith("https://example.com/page#inline-")
    hex_part = uri.split("#inline-")[1]
    assert len(hex_part) == 16
    assert all(c in "0123456789abcdef" for c in hex_part)
