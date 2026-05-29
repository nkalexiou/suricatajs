def test_protected_route_returns_401_without_key(client):
    response = client.get("/alerts")
    assert response.status_code in (401, 404)


def test_health_never_requires_key(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_get_api_key_rejects_wrong_key(client):
    response = client.get("/alerts", headers={"X-API-Key": "wrong"})
    assert response.status_code in (401, 404)


def test_create_token_returns_string():
    from api.auth import create_token
    token = create_token(1, "admin")
    assert isinstance(token, str)
    assert len(token) > 20


def test_decode_token_returns_correct_payload():
    from api.auth import create_token, decode_token
    token = create_token(42, "operator")
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "operator"


def test_hash_and_verify_password():
    from api.auth import hash_password, verify_password
    hashed = hash_password("mysecret")
    assert verify_password("mysecret", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_require_any_auth_accepts_api_key(client, auth_headers):
    """Existing X-API-Key auth still works on protected endpoints."""
    response = client.get("/alerts", headers=auth_headers)
    assert response.status_code == 200


def test_require_any_auth_accepts_jwt_cookie(client, admin_cookie):
    response = client.get("/alerts", cookies=admin_cookie)
    assert response.status_code == 200


def test_require_any_auth_rejects_no_auth(client):
    response = client.get("/alerts")
    assert response.status_code == 401


def test_require_any_auth_rejects_invalid_cookie(client):
    response = client.get("/alerts", cookies={"session": "not.a.valid.jwt"})
    assert response.status_code == 401
