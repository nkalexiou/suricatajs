import datetime
import pytest
from sqlalchemy import text
from db.database import get_engine
from api.auth import hash_password


def _seed_user(email, name, role="operator"):
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    with get_engine().begin() as conn:
        result = conn.execute(
            text("INSERT INTO users (email, name, password_hash, role, created_at) "
                 "VALUES (:email, :name, :hash, :role, :now)"),
            {"email": email, "name": name, "hash": hash_password("pass"), "role": role, "now": now},
        )
        return result.lastrowid


def test_list_users_requires_admin(client, operator_cookie):
    response = client.get("/users", cookies=operator_cookie)
    assert response.status_code == 403


def test_list_users_requires_auth(client):
    response = client.get("/users")
    assert response.status_code == 401


def test_list_users_as_admin(client, admin_cookie):
    _seed_user("op@test.com", "Op")
    response = client.get("/users", cookies=admin_cookie)
    assert response.status_code == 200
    data = response.json()
    emails = [u["email"] for u in data]
    assert "admin@localhost" in emails
    assert "op@test.com" in emails
    assert all("password_hash" not in u for u in data)


def test_create_user_as_admin(client, admin_cookie):
    response = client.post(
        "/users",
        json={"email": "new@test.com", "name": "New User", "password": "securepass1", "role": "operator"},
        cookies=admin_cookie,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@test.com"
    assert data["role"] == "operator"


def test_create_user_duplicate_email(client, admin_cookie):
    _seed_user("dup@test.com", "Dup")
    response = client.post(
        "/users",
        json={"email": "dup@test.com", "name": "Dup2", "password": "pass12345", "role": "operator"},
        cookies=admin_cookie,
    )
    assert response.status_code == 409


def test_create_user_requires_admin(client, operator_cookie):
    response = client.post(
        "/users",
        json={"email": "x@test.com", "name": "X", "password": "pass12345", "role": "operator"},
        cookies=operator_cookie,
    )
    assert response.status_code == 403


def test_delete_user(client, admin_cookie):
    uid = _seed_user("todelete@test.com", "Delete Me")
    response = client.delete(f"/users/{uid}", cookies=admin_cookie)
    assert response.status_code == 204


def test_delete_user_cannot_delete_self(client, admin_cookie):
    with get_engine().connect() as conn:
        admin_id = conn.execute(
            text("SELECT id FROM users WHERE email = 'admin@localhost'")
        ).scalar()
    response = client.delete(f"/users/{admin_id}", cookies=admin_cookie)
    assert response.status_code == 400


def test_delete_user_requires_admin(client, operator_cookie):
    uid = _seed_user("other@test.com", "Other")
    response = client.delete(f"/users/{uid}", cookies=operator_cookie)
    assert response.status_code == 403
