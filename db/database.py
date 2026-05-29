import os
import secrets
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
    """Upgrade tables for existing deployments."""
    engine = get_engine()
    url_str = str(engine.url)
    is_sqlite = url_str.startswith("sqlite")
    pk = _pk_type()

    insp = sa_inspect(engine)
    existing_tables = insp.get_table_names()

    # --- alerts table migration (pre-v2 → v2) ---
    if "alerts" in existing_tables:
        cols = {c["name"] for c in insp.get_columns("alerts")}
        if "id" not in cols:
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

    # --- targets table migration (v2 → v3: add crawl_depth, use_playwright) ---
    if "targets" in existing_tables:
        cols = {c["name"] for c in insp.get_columns("targets")}
        if "crawl_depth" not in cols or "use_playwright" not in cols:
            with engine.begin() as conn:
                if "crawl_depth" not in cols:
                    if is_sqlite:
                        conn.execute(text("ALTER TABLE targets ADD COLUMN crawl_depth INTEGER NOT NULL DEFAULT 0"))
                    else:
                        conn.execute(text("ALTER TABLE targets ADD COLUMN IF NOT EXISTS crawl_depth INTEGER NOT NULL DEFAULT 0"))
                if "use_playwright" not in cols:
                    if is_sqlite:
                        conn.execute(text("ALTER TABLE targets ADD COLUMN use_playwright INTEGER NOT NULL DEFAULT 0"))
                    else:
                        conn.execute(text("ALTER TABLE targets ADD COLUMN IF NOT EXISTS use_playwright INTEGER NOT NULL DEFAULT 0"))

    # --- alerts table migration (v3: add sri column) ---
    if "alerts" in existing_tables:
        cols = {c["name"] for c in insp.get_columns("alerts")}
        if "sri" not in cols:
            with engine.begin() as conn:
                if is_sqlite:
                    conn.execute(text("ALTER TABLE alerts ADD COLUMN sri TEXT"))
                else:
                    conn.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS sri TEXT"))

    # --- alerts table migration (v4: add resolved columns) ---
    if "alerts" in existing_tables:
        cols = {c["name"] for c in insp.get_columns("alerts")}
        with engine.begin() as conn:
            if "resolved" not in cols:
                if is_sqlite:
                    conn.execute(text("ALTER TABLE alerts ADD COLUMN resolved INTEGER NOT NULL DEFAULT 0"))
                else:
                    conn.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS resolved INTEGER NOT NULL DEFAULT 0"))
            if "resolved_at" not in cols:
                if is_sqlite:
                    conn.execute(text("ALTER TABLE alerts ADD COLUMN resolved_at TEXT"))
                else:
                    conn.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS resolved_at TEXT"))
            if "resolved_by" not in cols:
                if is_sqlite:
                    conn.execute(text("ALTER TABLE alerts ADD COLUMN resolved_by INTEGER"))
                else:
                    conn.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS resolved_by INTEGER"))

    # --- targets table migration (v4: add domain_id) ---
    if "targets" in existing_tables:
        cols = {c["name"] for c in insp.get_columns("targets")}
        if "domain_id" not in cols:
            with engine.begin() as conn:
                if is_sqlite:
                    conn.execute(text("ALTER TABLE targets ADD COLUMN domain_id INTEGER"))
                else:
                    conn.execute(text("ALTER TABLE targets ADD COLUMN IF NOT EXISTS domain_id INTEGER"))

    # --- targets table migration (v5: add last_scanned_at) ---
    if "targets" in existing_tables:
        cols = {c["name"] for c in insp.get_columns("targets")}
        if "last_scanned_at" not in cols:
            with engine.begin() as conn:
                if is_sqlite:
                    conn.execute(text("ALTER TABLE targets ADD COLUMN last_scanned_at TEXT"))
                else:
                    conn.execute(text("ALTER TABLE targets ADD COLUMN IF NOT EXISTS last_scanned_at TEXT"))

    # --- alerts table migration (v6: add source_page) ---
    if "alerts" in existing_tables:
        cols = {c["name"] for c in insp.get_columns("alerts")}
        if "source_page" not in cols:
            with engine.begin() as conn:
                if is_sqlite:
                    conn.execute(text("ALTER TABLE alerts ADD COLUMN source_page TEXT"))
                else:
                    conn.execute(text("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS source_page TEXT"))


def _bootstrap_admin():
    """Create initial admin user on first startup. No-op if users exist."""
    import logging
    logger = logging.getLogger("suricatajs")
    engine = get_engine()
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
    if count > 0:
        return
    import bcrypt as _bcrypt
    import datetime
    password = secrets.token_urlsafe(10)
    password_hash = _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO users (email, name, password_hash, role, created_at) "
                 "VALUES (:email, :name, :hash, :role, :created_at)"),
            {"email": "admin@localhost", "name": "Admin",
             "hash": password_hash, "role": "admin", "created_at": now},
        )
    border = "=" * 60
    logger.warning(border)
    logger.warning(f"Admin password (one-time): {password}")
    logger.warning("Login: http://localhost:8085  |  user: admin@localhost")
    logger.warning("Change this password under Profile after first login.")
    logger.warning(border)


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
                diff TEXT,
                sri TEXT,
                resolved INTEGER NOT NULL DEFAULT 0,
                resolved_at TEXT,
                resolved_by INTEGER,
                source_page TEXT
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
                created_at TEXT NOT NULL,
                crawl_depth INTEGER NOT NULL DEFAULT 0,
                use_playwright INTEGER NOT NULL DEFAULT 0,
                domain_id INTEGER,
                last_scanned_at TEXT
            )
        """))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS users (
                id {pk},
                email TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'operator',
                created_at TEXT NOT NULL
            )
        """))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS domains (
                id {pk},
                domain TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
        """))
    _bootstrap_admin()
