import os

# Set env vars before any app imports so SQLAlchemy and auth pick them up
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["API_KEYS"] = "test-key"
os.environ["JWT_SECRET"] = "test-jwt-secret-32-chars-minimum!!"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text


@pytest.fixture(autouse=True)
def fresh_db():
    """Reset the in-memory DB before each test."""
    from db.database import reset_engine, init_db
    reset_engine()
    init_db()
    yield
    from db.database import get_engine
    with get_engine().connect() as conn:
        for tbl in ("targets", "alerts", "suricatajs", "users", "domains"):
            conn.execute(text(f"DROP TABLE IF EXISTS {tbl}"))
        conn.commit()
    reset_engine()


@pytest.fixture
def client():
    from api.main import app
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-API-Key": "test-key"}


@pytest.fixture
def admin_cookie(fresh_db):
    """Return cookies dict with a valid JWT for the bootstrap admin user."""
    from db.database import get_engine
    from api.auth import create_token
    with get_engine().connect() as conn:
        row = conn.execute(
            text("SELECT id FROM users WHERE email = 'admin@localhost'")
        ).fetchone()
    assert row, "Admin user not created by bootstrap"
    token = create_token(row[0], "admin")
    return {"session": token}


@pytest.fixture
def operator_cookie(fresh_db):
    """Return cookies dict with a valid JWT for a freshly created operator user."""
    import datetime
    from db.database import get_engine
    from api.auth import create_token, hash_password
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    with get_engine().begin() as conn:
        result = conn.execute(
            text("INSERT INTO users (email, name, password_hash, role, created_at) "
                 "VALUES ('op@example.com', 'Operator', :hash, 'operator', :now)"),
            {"hash": hash_password("oppass"), "now": now},
        )
        op_id = result.lastrowid
    token = create_token(op_id, "operator")
    return {"session": token}
