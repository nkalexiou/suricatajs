import os

# Set env vars before any app imports so SQLAlchemy and auth pick them up
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["API_KEYS"] = "test-key"

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
        conn.execute(text("DROP TABLE IF EXISTS targets"))
        conn.execute(text("DROP TABLE IF EXISTS alerts"))
        conn.execute(text("DROP TABLE IF EXISTS suricatajs"))
        conn.commit()
    reset_engine()


@pytest.fixture
def client():
    from api.main import app
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-API-Key": "test-key"}
