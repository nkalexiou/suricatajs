from sqlalchemy import text, inspect as sa_inspect
from db.database import get_engine, init_db


def test_users_table_created():
    engine = get_engine()
    insp = sa_inspect(engine)
    assert "users" in insp.get_table_names()
    cols = {c["name"] for c in insp.get_columns("users")}
    assert cols >= {"id", "email", "name", "password_hash", "role", "created_at"}


def test_domains_table_created():
    engine = get_engine()
    insp = sa_inspect(engine)
    assert "domains" in insp.get_table_names()
    cols = {c["name"] for c in insp.get_columns("domains")}
    assert cols >= {"id", "domain", "created_at"}


def test_targets_has_domain_id():
    engine = get_engine()
    insp = sa_inspect(engine)
    cols = {c["name"] for c in insp.get_columns("targets")}
    assert "domain_id" in cols


def test_alerts_has_resolved_columns():
    engine = get_engine()
    insp = sa_inspect(engine)
    cols = {c["name"] for c in insp.get_columns("alerts")}
    assert "resolved" in cols
    assert "resolved_at" in cols
    assert "resolved_by" in cols


def test_admin_bootstrap_creates_admin_user():
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT email, role FROM users WHERE email = 'admin@localhost'")
        ).fetchone()
    assert row is not None
    assert row[1] == "admin"


def test_admin_bootstrap_skipped_when_users_exist():
    """Bootstrap should not create a second admin if users already exist."""
    from db.database import reset_engine
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(
            text("INSERT INTO users (email, name, password_hash, role, created_at) "
                 "VALUES ('other@example.com', 'Other', 'x', 'operator', '20260529_000000')")
        )
        conn.commit()
    count_before = engine.connect().execute(text("SELECT COUNT(*) FROM users")).scalar()
    init_db()  # second call should not add another admin
    count_after = engine.connect().execute(text("SELECT COUNT(*) FROM users")).scalar()
    assert count_after == count_before


def test_init_db_creates_tables(fresh_db):
    from db.database import get_engine
    engine = get_engine()
    with engine.connect() as conn:
        tables = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        ).fetchall()
    names = {row[0] for row in tables}
    assert "suricatajs" in names
    assert "alerts" in names


def test_get_connection_yields_usable_connection(fresh_db):
    from db.database import get_connection
    with get_connection() as conn:
        result = conn.execute(text("SELECT 1")).fetchone()
    assert result[0] == 1


def test_targets_has_crawl_depth_and_use_playwright():
    from sqlalchemy import inspect as sa_inspect
    from db.database import get_engine
    insp = sa_inspect(get_engine())
    cols = {c["name"] for c in insp.get_columns("targets")}
    assert "crawl_depth" in cols
    assert "use_playwright" in cols


def test_migrate_db_adds_columns_to_existing_targets():
    from sqlalchemy import inspect as sa_inspect
    from db.database import reset_engine, get_engine
    from db.database import _migrate_db
    from sqlalchemy import text

    reset_engine()
    engine = get_engine()

    # Create targets table without the new columns (simulates pre-v3 deployment)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE targets (
                id INTEGER PRIMARY KEY,
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

    _migrate_db()

    insp = sa_inspect(engine)
    cols = {c["name"] for c in insp.get_columns("targets")}
    assert "crawl_depth" in cols
    assert "use_playwright" in cols

    reset_engine()
