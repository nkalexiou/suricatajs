import pytest
from sqlalchemy import text
from db.database import get_engine


def _seed_alert(javascript, alert_type):
    with get_engine().connect() as conn:
        conn.execute(
            text("INSERT INTO alerts (javascript, stored_checksum, new_checksum, date, alert_msg, alert_type) "
                 "VALUES (:js, NULL, NULL, '20260528_120000', 'ALERT', :type)"),
            {"js": javascript, "type": alert_type},
        )
        conn.commit()


def _seed_script(uri):
    with get_engine().connect() as conn:
        conn.execute(
            text("INSERT INTO suricatajs (uri, javascript, checksum, date) "
                 "VALUES (:uri, 'var x=1;', 'abc', '20260528_120000')"),
            {"uri": uri},
        )
        conn.commit()


def _seed_target(url):
    with get_engine().connect() as conn:
        conn.execute(
            text("INSERT INTO targets (url, created_at) VALUES (:url, '20260528_120000')"),
            {"url": url},
        )
        conn.commit()


def test_metrics_no_auth_required(client):
    response = client.get("/metrics")
    assert response.status_code == 200


def test_metrics_content_type(client):
    response = client.get("/metrics")
    assert "text/plain" in response.headers["content-type"]


def test_metrics_empty_db(client):
    response = client.get("/metrics")
    body = response.text
    assert "suricatajs_scripts_total" in body
    assert "suricatajs_targets_total" in body
    assert "suricatajs_last_scan_timestamp_seconds" in body


def test_metrics_counts_alerts_by_type(client):
    _seed_alert("https://a.com/a.js", "new_script")
    _seed_alert("https://a.com/b.js", "new_script")
    _seed_alert("https://a.com/c.js", "checksum")
    response = client.get("/metrics")
    body = response.text
    assert 'suricatajs_alerts_total{alert_type="new_script"}' in body
    assert 'suricatajs_alerts_total{alert_type="checksum"}' in body


def test_metrics_scripts_total(client):
    _seed_script("https://a.com/a.js")
    _seed_script("https://a.com/b.js")
    response = client.get("/metrics")
    body = response.text
    assert "suricatajs_scripts_total 2.0" in body


def test_metrics_targets_total(client):
    _seed_target("https://a.com")
    _seed_target("https://b.com")
    response = client.get("/metrics")
    body = response.text
    assert "suricatajs_targets_total 2.0" in body


def test_metrics_last_scan_timestamp(client):
    _seed_script("https://a.com/a.js")
    response = client.get("/metrics")
    body = response.text
    assert "suricatajs_last_scan_timestamp_seconds" in body
    for line in body.splitlines():
        if "suricatajs_last_scan_timestamp_seconds" in line and not line.startswith("#"):
            assert float(line.split()[-1]) > 0
            break
