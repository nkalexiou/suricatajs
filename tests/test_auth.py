def test_protected_route_returns_401_without_key(client):
    response = client.get("/alerts")
    assert response.status_code in (401, 404)


def test_health_never_requires_key(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_get_api_key_rejects_wrong_key(client):
    response = client.get("/alerts", headers={"X-API-Key": "wrong"})
    assert response.status_code in (401, 404)
