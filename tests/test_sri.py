import base64
import hashlib
from sqlalchemy import text
from db.database import get_engine


def _sri(content: str) -> str:
    digest = hashlib.sha384(content.encode("utf-8")).digest()
    return "sha384-" + base64.b64encode(digest).decode("ascii")


def test_compute_sri_format():
    from scanner.engine import _compute_sri
    result = _compute_sri("var x = 1;")
    assert result.startswith("sha384-")
    b64_part = result[len("sha384-"):]
    assert len(b64_part) == 64


def test_compute_sri_correctness():
    from scanner.engine import _compute_sri
    content = "var x = 1;"
    assert _compute_sri(content) == _sri(content)


def test_alerts_schema_has_sri(client, auth_headers):
    with get_engine().connect() as conn:
        conn.execute(
            text("INSERT INTO alerts (javascript, stored_checksum, new_checksum, date, alert_msg, alert_type, sri) "
                 "VALUES ('https://a.com/a.js', NULL, NULL, '20260528_120000', 'ALERT', 'new_script', :sri)"),
            {"sri": _sri("var x=1;")},
        )
        conn.commit()
    response = client.get("/alerts", headers=auth_headers)
    alert = response.json()[0]
    assert "sri" in alert
    assert alert["sri"].startswith("sha384-")


def test_alerts_sri_is_none_when_not_set(client, auth_headers):
    with get_engine().connect() as conn:
        conn.execute(
            text("INSERT INTO alerts (javascript, stored_checksum, new_checksum, date, alert_msg, alert_type) "
                 "VALUES ('https://a.com/a.js', NULL, NULL, '20260528_120000', 'ALERT', 'new_script')"),
        )
        conn.commit()
    response = client.get("/alerts", headers=auth_headers)
    alert = response.json()[0]
    assert "sri" in alert
    assert alert["sri"] is None


def test_scanner_stores_sri_on_new_script(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/t.db")
    from db.database import reset_engine, init_db
    reset_engine()
    init_db()

    js_content = "var version = '2';"
    expected_sri = _sri(js_content)

    from unittest.mock import patch, MagicMock
    mock_resp = MagicMock()
    mock_resp.text = js_content

    with patch("scanner.engine.requests.get", return_value=mock_resp):
        from scanner.engine import _scan_external_script
        _scan_external_script("https://a.com/a.js", "https://example.com/")

    from db.database import get_engine as ge
    from sqlalchemy import text as sql_text
    with ge().connect() as conn:
        row = conn.execute(sql_text("SELECT sri FROM alerts")).fetchone()
    assert row[0] == expected_sri
    reset_engine()
