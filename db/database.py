import os
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

_engine = None


def _build_engine():
    url = os.getenv("DATABASE_URL", "sqlite:///./db/surikatajs.db")
    if url.startswith("sqlite"):
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(url)


def get_engine():
    global _engine
    if _engine is None:
        _engine = _build_engine()
    return _engine


def reset_engine():
    """Dispose and clear the engine singleton. Used in tests."""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None


@contextmanager
def get_connection():
    engine = get_engine()
    with engine.connect() as conn:
        yield conn


def init_db():
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS suricatajs (
                uri TEXT,
                javascript TEXT,
                checksum TEXT,
                date TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS alerts (
                javascript TEXT,
                stored_checksum TEXT,
                new_checksum TEXT,
                date TEXT,
                alert_msg TEXT,
                alert_type TEXT
            )
        """))
        conn.commit()
