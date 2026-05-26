from sqlalchemy import text
from db.database import get_engine


def _seed_alert(javascript, alert_type, stored_checksum=None, new_checksum=None):
    with get_engine().connect() as conn:
        conn.execute(
            text("INSERT INTO alerts "
                 "(javascript, stored_checksum, new_checksum, date, alert_msg, alert_type) "
                 "VALUES (:js, :stored, :new, :date, :msg, :type)"),
            {
                "js": javascript, "stored": stored_checksum, "new": new_checksum,
                "date": "20260525_120000", "msg": "ALERT: test", "type": alert_type,
            },
        )
        conn.commit()


def test_get_alerts_requires_api_key(client):
    response = client.get("/alerts")
    assert response.status_code == 401


def test_get_alerts_empty(client, auth_headers):
    response = client.get("/alerts", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_get_alerts_returns_all(client, auth_headers):
    _seed_alert("https://example.com/a.js", "new_script")
    _seed_alert("https://example.com/b.js", "checksum", "old", "new")
    response = client.get("/alerts", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_alerts_filter_by_type(client, auth_headers):
    _seed_alert("https://example.com/a.js", "new_script")
    _seed_alert("https://example.com/b.js", "checksum", "old", "new")
    response = client.get("/alerts?type=new_script", headers=auth_headers)
    data = response.json()
    assert len(data) == 1
    assert data[0]["alert_type"] == "new_script"


def test_get_alerts_filter_by_javascript(client, auth_headers):
    _seed_alert("https://example.com/a.js", "new_script")
    _seed_alert("https://example.com/b.js", "new_script")
    response = client.get(
        "/alerts",
        params={"javascript": "https://example.com/a.js"},
        headers=auth_headers,
    )
    data = response.json()
    assert len(data) == 1
    assert data[0]["javascript"] == "https://example.com/a.js"


def test_get_alerts_filter_by_date(client, auth_headers):
    _seed_alert("https://example.com/a.js", "new_script")
    response = client.get("/alerts?date=20260525_120000", headers=auth_headers)
    data = response.json()
    assert len(data) == 1
    assert data[0]["date"] == "20260525_120000"


def test_alert_response_schema(client, auth_headers):
    _seed_alert("https://example.com/a.js", "new_script")
    data = client.get("/alerts", headers=auth_headers).json()
    alert = data[0]
    assert "javascript" in alert
    assert "stored_checksum" in alert
    assert "new_checksum" in alert
    assert "date" in alert
    assert "alert_msg" in alert
    assert "alert_type" in alert
