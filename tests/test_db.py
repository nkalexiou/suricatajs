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
