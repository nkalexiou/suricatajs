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


def test_get_alerts_rejects_when_api_keys_not_configured(monkeypatch):
    monkeypatch.delenv("API_KEYS", raising=False)
    from api.main import create_app
    from fastapi.testclient import TestClient
    c = TestClient(create_app())
    response = c.get("/alerts")
    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorized"


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
    assert "id" in alert
    assert "javascript" in alert
    assert "stored_checksum" in alert
    assert "new_checksum" in alert
    assert "date" in alert
    assert "alert_msg" in alert
    assert "alert_type" in alert
    assert "diff" in alert


def test_get_alerts_default_shows_open_only(client, auth_headers):
    """Default GET /alerts returns only unresolved alerts."""
    _seed_alert("https://example.com/a.js", "new_script")
    with get_engine().begin() as conn:
        conn.execute(
            text("INSERT INTO alerts (javascript, stored_checksum, new_checksum, date, alert_msg, alert_type, resolved) "
                 "VALUES ('https://example.com/b.js', null, null, '20260529_000000', 'msg', 'new_script', 1)")
        )
    response = client.get("/alerts", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["javascript"] == "https://example.com/a.js"


def test_get_alerts_resolved_filter(client, auth_headers):
    _seed_alert("https://example.com/open.js", "new_script")
    with get_engine().begin() as conn:
        conn.execute(
            text("INSERT INTO alerts (javascript, date, alert_msg, alert_type, resolved) "
                 "VALUES ('https://example.com/closed.js', '20260529_000000', 'msg', 'new_script', 1)")
        )
    data = client.get("/alerts?resolved=1", headers=auth_headers).json()
    assert len(data) == 1
    assert data[0]["javascript"] == "https://example.com/closed.js"


def test_resolve_alert(client, admin_cookie):
    _seed_alert("https://example.com/a.js", "checksum", "old", "new")
    alert_id = client.get("/alerts", cookies=admin_cookie).json()[0]["id"]
    response = client.patch(f"/alerts/{alert_id}/resolve", cookies=admin_cookie)
    assert response.status_code == 200
    data = response.json()
    assert data["resolved"] is True
    assert data["resolved_at"] is not None
    open_alerts = client.get("/alerts", cookies=admin_cookie).json()
    assert not any(a["id"] == alert_id for a in open_alerts)


def test_resolve_alert_not_found(client, admin_cookie):
    assert client.patch("/alerts/9999/resolve", cookies=admin_cookie).status_code == 404


def test_resolve_requires_auth(client):
    assert client.patch("/alerts/1/resolve").status_code == 401


def test_approve_alert_updates_baseline(client, admin_cookie):
    with get_engine().begin() as conn:
        conn.execute(
            text("INSERT INTO suricatajs (uri, javascript, checksum, date) "
                 "VALUES ('https://cdn.example.com/app.js', 'var old=1', 'oldhash', '20260529_000000')")
        )
    _seed_alert("https://cdn.example.com/app.js", "checksum", "oldhash", "newhash")
    alert_id = client.get("/alerts", cookies=admin_cookie).json()[0]["id"]
    response = client.patch(f"/alerts/{alert_id}/approve", cookies=admin_cookie)
    assert response.status_code == 200
    assert response.json()["resolved"] is True
    with get_engine().connect() as conn:
        row = conn.execute(
            text("SELECT checksum FROM suricatajs WHERE uri = 'https://cdn.example.com/app.js' ORDER BY date DESC LIMIT 1")
        ).fetchone()
    assert row[0] == "newhash"


def test_approve_alert_with_no_new_checksum_returns_400(client, admin_cookie):
    _seed_alert("https://example.com/new.js", "new_script")
    alert_id = client.get("/alerts", cookies=admin_cookie).json()[0]["id"]
    response = client.patch(f"/alerts/{alert_id}/approve", cookies=admin_cookie)
    assert response.status_code == 400
