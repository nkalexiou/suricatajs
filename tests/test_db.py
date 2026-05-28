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
    from db.database import reset_engine, init_db, get_engine
    from sqlalchemy import inspect as sa_inspect
    reset_engine()
    init_db()
    engine = get_engine()
    insp = sa_inspect(engine)
    cols = {c["name"] for c in insp.get_columns("targets")}
    assert "crawl_depth" in cols
    assert "use_playwright" in cols
    reset_engine()
