import pytest
from sqlalchemy import text
from db.database import get_engine


def _seed_domain(domain):
    with get_engine().begin() as conn:
        result = conn.execute(
            text("INSERT INTO domains (domain, created_at) VALUES (:d, '20260529_000000')"),
            {"d": domain},
        )
        return result.lastrowid


def test_list_domains_requires_auth(client):
    assert client.get("/domains").status_code == 401


def test_list_domains_empty(client, admin_cookie):
    response = client.get("/domains", cookies=admin_cookie)
    assert response.status_code == 200
    assert response.json() == []


def test_create_domain(client, admin_cookie):
    response = client.post("/domains", json={"domain": "example.com"}, cookies=admin_cookie)
    assert response.status_code == 201
    data = response.json()
    assert data["domain"] == "example.com"
    assert "id" in data
    assert "created_at" in data


def test_create_domain_duplicate(client, admin_cookie):
    client.post("/domains", json={"domain": "example.com"}, cookies=admin_cookie)
    response = client.post("/domains", json={"domain": "example.com"}, cookies=admin_cookie)
    assert response.status_code == 409


def test_list_domains_returns_created(client, admin_cookie):
    client.post("/domains", json={"domain": "a.com"}, cookies=admin_cookie)
    client.post("/domains", json={"domain": "b.com"}, cookies=admin_cookie)
    data = client.get("/domains", cookies=admin_cookie).json()
    assert len(data) == 2
    assert {d["domain"] for d in data} == {"a.com", "b.com"}


def test_delete_domain(client, admin_cookie):
    resp = client.post("/domains", json={"domain": "todelete.com"}, cookies=admin_cookie)
    domain_id = resp.json()["id"]
    response = client.delete(f"/domains/{domain_id}", cookies=admin_cookie)
    assert response.status_code == 204


def test_delete_domain_blocked_when_targets_assigned(client, admin_cookie):
    resp = client.post("/domains", json={"domain": "blocked.com"}, cookies=admin_cookie)
    domain_id = resp.json()["id"]
    with get_engine().begin() as conn:
        conn.execute(
            text("INSERT INTO targets (url, created_at, domain_id) VALUES ('https://blocked.com/', '20260529_000000', :did)"),
            {"did": domain_id},
        )
    response = client.delete(f"/domains/{domain_id}", cookies=admin_cookie)
    assert response.status_code == 400
    assert "targets" in response.json()["detail"].lower()


def test_delete_domain_not_found(client, admin_cookie):
    assert client.delete("/domains/9999", cookies=admin_cookie).status_code == 404


def test_operator_can_list_and_create_domains(client, operator_cookie):
    response = client.post("/domains", json={"domain": "op.com"}, cookies=operator_cookie)
    assert response.status_code == 201
    assert client.get("/domains", cookies=operator_cookie).status_code == 200
