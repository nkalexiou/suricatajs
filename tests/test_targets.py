# tests/test_targets.py
import pytest
from sqlalchemy import text
from db.database import get_engine


def _seed_target(url, name=None, scan_interval_minutes=None):
    with get_engine().connect() as conn:
        conn.execute(
            text("INSERT INTO targets (url, name, scan_interval_minutes, created_at) "
                 "VALUES (:url, :name, :interval, :created_at)"),
            {"url": url, "name": name, "interval": scan_interval_minutes,
             "created_at": "20260526_120000"},
        )
        conn.commit()


def test_list_targets_empty(client, auth_headers):
    response = client.get("/targets", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_list_targets_returns_all(client, auth_headers):
    _seed_target("https://example.com/a", name="Site A")
    _seed_target("https://example.com/b", name="Site B")
    response = client.get("/targets", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_create_target(client, auth_headers):
    payload = {
        "url": "https://example.com",
        "name": "Example",
        "tags": ["ecommerce"],
        "owner": "ops",
        "scan_interval_minutes": 30,
    }
    response = client.post("/targets", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["url"] == "https://example.com"
    assert data["name"] == "Example"
    assert data["tags"] == ["ecommerce"]
    assert data["owner"] == "ops"
    assert data["scan_interval_minutes"] == 30
    assert "id" in data
    assert "created_at" in data


def test_create_target_duplicate_url(client, auth_headers):
    payload = {"url": "https://example.com"}
    client.post("/targets", json=payload, headers=auth_headers)
    response = client.post("/targets", json=payload, headers=auth_headers)
    assert response.status_code == 409


def test_delete_target(client, auth_headers):
    _seed_target("https://example.com")
    targets = client.get("/targets", headers=auth_headers).json()
    target_id = targets[0]["id"]
    response = client.delete(f"/targets/{target_id}", headers=auth_headers)
    assert response.status_code == 204
    assert client.get("/targets", headers=auth_headers).json() == []


def test_delete_nonexistent_target(client, auth_headers):
    response = client.delete("/targets/9999", headers=auth_headers)
    assert response.status_code == 404


def test_targets_requires_api_key(client):
    assert client.get("/targets").status_code == 401
    assert client.post("/targets", json={"url": "https://x.com"}).status_code == 401


def test_target_schema(client, auth_headers):
    payload = {"url": "https://example.com", "name": "Test"}
    data = client.post("/targets", json=payload, headers=auth_headers).json()
    for field in ["id", "url", "name", "tags", "owner", "scan_interval_minutes",
                  "approved_checksum", "approval_note", "approved_at", "created_at",
                  "crawl_depth", "use_playwright"]:
        assert field in data


def test_create_target_with_crawl_and_playwright(client, auth_headers):
    payload = {
        "url": "https://example.com",
        "crawl_depth": 2,
        "use_playwright": True,
    }
    data = client.post("/targets", json=payload, headers=auth_headers).json()
    assert data["crawl_depth"] == 2
    assert data["use_playwright"] is True


def test_create_target_defaults_crawl_depth_and_playwright(client, auth_headers):
    payload = {"url": "https://example.com"}
    data = client.post("/targets", json=payload, headers=auth_headers).json()
    assert data["crawl_depth"] == 0
    assert data["use_playwright"] is False


def test_approve_target(client, auth_headers):
    _seed_target("https://example.com")
    targets = client.get("/targets", headers=auth_headers).json()
    target_id = targets[0]["id"]
    response = client.post(f"/targets/{target_id}/approve",
                           json={"note": "Looks good"}, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["approval_note"] == "Looks good"
    assert data["approved_at"] is not None


def test_approve_nonexistent_target(client, auth_headers):
    response = client.post("/targets/9999/approve", json={}, headers=auth_headers)
    assert response.status_code == 404
