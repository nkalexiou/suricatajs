import datetime
import pytest


def test_login_with_known_user(client):
    from db.database import get_engine
    from api.auth import hash_password
    from sqlalchemy import text
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    with get_engine().begin() as conn:
        conn.execute(
            text("INSERT INTO users (email, name, password_hash, role, created_at) "
                 "VALUES ('user@test.com', 'Test', :hash, 'operator', :now)"),
            {"hash": hash_password("testpass123"), "now": now},
        )
    response = client.post("/auth/login", json={"email": "user@test.com", "password": "testpass123"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "user@test.com"
    assert data["role"] == "operator"
    assert "session" in response.cookies


def test_login_wrong_password(client):
    response = client.post("/auth/login", json={"email": "admin@localhost", "password": "badpass"})
    assert response.status_code == 401


def test_login_unknown_email(client):
    response = client.post("/auth/login", json={"email": "nobody@x.com", "password": "x"})
    assert response.status_code == 401


def test_logout_clears_cookie(client, admin_cookie):
    response = client.post("/auth/logout", cookies=admin_cookie)
    assert response.status_code == 200
    assert response.cookies.get("session", "") == ""


def test_me_returns_current_user(client, admin_cookie):
    response = client.get("/auth/me", cookies=admin_cookie)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@localhost"
    assert data["role"] == "admin"
    assert "password_hash" not in data


def test_me_requires_auth(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_patch_me_updates_name(client, admin_cookie):
    response = client.patch("/auth/me", json={"name": "New Name"}, cookies=admin_cookie)
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


def test_patch_me_updates_password(client, admin_cookie):
    response = client.patch(
        "/auth/me",
        json={"password": "newpassword123"},
        cookies=admin_cookie,
    )
    assert response.status_code == 200
    me = client.get("/auth/me", cookies=admin_cookie).json()
    response = client.post(
        "/auth/login", json={"email": me["email"], "password": "newpassword123"}
    )
    assert response.status_code == 200
