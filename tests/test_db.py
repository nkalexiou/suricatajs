from sqlalchemy import text


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
