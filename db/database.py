import os
import threading
from contextlib import contextmanager
from sqlalchemy import create_engine, inspect as sa_inspect, text
from sqlalchemy.pool import StaticPool

_engine = None
_engine_lock = threading.Lock()


def _build_engine():
    url = os.getenv("DATABASE_URL", "sqlite:///./db/surikatajs.db")
    if url.startswith("sqlite"):
        if url == "sqlite://" or url.startswith("sqlite:///:memory:"):
            return create_engine(
                url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
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


def _pk_type():
    url = os.getenv("DATABASE_URL", "sqlite:///./db/surikatajs.db")
    return "INTEGER PRIMARY KEY" if url.startswith("sqlite") else "SERIAL PRIMARY KEY"


def _migrate_db():
    """Upgrade alerts table to add id and diff columns for existing deployments."""
    engine = get_engine()
    url_str = str(engine.url)
    is_sqlite = url_str.startswith("sqlite")
    pk = _pk_type()

    insp = sa_inspect(engine)
    if "alerts" not in insp.get_table_names():
        return  # fresh install; init_db will create with correct schema

    cols = {c["name"] for c in insp.get_columns("alerts")}
    if "id" in cols:
        return  # already migrated

    with engine.begin() as conn:
        if is_sqlite:
            conn.execute(text("ALTER TABLE alerts RENAME TO _alerts_pre_v2"))
            conn.execute(text(f"""
                CREATE TABLE alerts (
                    id {pk},
                    javascript TEXT,
                    stored_checksum TEXT,
                    new_checksum TEXT,
                    date TEXT,
                    alert_msg TEXT,
                    alert_type TEXT,
                    diff TEXT
                )
            """))
            conn.execute(text("""
                INSERT INTO alerts (javascript, stored_checksum, new_checksum, date, alert_msg, alert_type)
                SELECT javascript, stored_checksum, new_checksum, date, alert_msg, alert_type
                FROM _alerts_pre_v2
            """))
            conn.execute(text("DROP TABLE _alerts_pre_v2"))
        else:
            conn.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS diff TEXT"))


def init_db():
    _migrate_db()
    engine = get_engine()
    pk = _pk_type()
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS suricatajs (
                uri TEXT,
                javascript TEXT,
                checksum TEXT,
                date TEXT
            )
        """))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS alerts (
                id {pk},
                javascript TEXT,
                stored_checksum TEXT,
                new_checksum TEXT,
                date TEXT,
                alert_msg TEXT,
                alert_type TEXT,
                diff TEXT
            )
        """))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS targets (
                id {pk},
                url TEXT NOT NULL UNIQUE,
                name TEXT,
                tags TEXT,
                owner TEXT,
                scan_interval_minutes INTEGER,
                approved_checksum TEXT,
                approval_note TEXT,
                approved_at TEXT,
                created_at TEXT NOT NULL
            )
        """))
