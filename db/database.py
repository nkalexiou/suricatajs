import os
import threading
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

_engine = None
_engine_lock = threading.Lock()


def _build_engine():
    url = os.getenv("DATABASE_URL", "sqlite:///./db/surikatajs.db")
    if url.startswith("sqlite"):
        if url == "sqlite://" or url.startswith("sqlite:///:memory:"):
            # In-memory SQLite: use StaticPool so all connections share one DB
            return create_engine(
                url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        # On-disk SQLite: use default pool
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url)


def get_engine():
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = _build_engine()
    return _engine


def reset_engine():
    """Dispose and clear the engine singleton. Used in tests."""
    global _engine
    with _engine_lock:
        if _engine is not None:
            _engine.dispose()
            _engine = None


@contextmanager
def get_connection():
    engine = get_engine()
    with engine.begin() as conn:
        yield conn


def init_db():
    engine = get_engine()
    with engine.begin() as conn:
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
