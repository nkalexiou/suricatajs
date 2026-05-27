# tests/test_loader.py
import json
import os
import tempfile
import pytest
from db.database import get_engine
from sqlalchemy import text


def _seed_target_in_db(url, name=None, scan_interval_minutes=None):
    with get_engine().connect() as conn:
        conn.execute(
            text("INSERT INTO targets (url, name, scan_interval_minutes, created_at) "
                 "VALUES (:url, :name, :interval, '20260526_120000')"),
            {"url": url, "name": name, "interval": scan_interval_minutes},
        )
        conn.commit()


def test_load_targets_from_db(fresh_db):
    _seed_target_in_db("https://example.com/a", name="Site A", scan_interval_minutes=30)
    _seed_target_in_db("https://example.com/b", name="Site B")
    from scanner.loader import load_targets
    targets = load_targets()
    assert len(targets) == 2
    urls = {t["url"] for t in targets}
    assert "https://example.com/a" in urls
    assert "https://example.com/b" in urls


def test_load_targets_from_txt_file(fresh_db):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("https://site-a.com\n")
        f.write("https://site-b.com\n")
        f.write("\n")
        f.write("# comment line\n")
        path = f.name
    try:
        from scanner.loader import load_targets
        targets = load_targets(path)
        urls = {t["url"] for t in targets}
        assert "https://site-a.com" in urls
        assert "https://site-b.com" in urls
        assert len(targets) == 2
    finally:
        os.unlink(path)


def test_load_targets_from_yaml_file(fresh_db):
    yaml_content = """
targets:
  - url: https://shop.example.com
    name: Shop
    tags:
      - ecommerce
    owner: alice
    scan_interval_minutes: 15
  - url: https://blog.example.com
    name: Blog
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        path = f.name
    try:
        from scanner.loader import load_targets
        targets = load_targets(path)
        assert len(targets) == 2
        shop = next(t for t in targets if t["url"] == "https://shop.example.com")
        assert shop["name"] == "Shop"
        assert shop["tags"] == ["ecommerce"]
        assert shop["owner"] == "alice"
        assert shop["scan_interval_minutes"] == 15
    finally:
        os.unlink(path)


def test_load_targets_db_takes_priority_over_file(fresh_db):
    _seed_target_in_db("https://db.example.com")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("https://file.example.com\n")
        path = f.name
    try:
        from scanner.loader import load_targets
        targets = load_targets(path)
        urls = {t["url"] for t in targets}
        assert "https://db.example.com" in urls
        assert "https://file.example.com" not in urls
    finally:
        os.unlink(path)


def test_load_targets_empty_file_returns_empty(fresh_db):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        path = f.name
    try:
        from scanner.loader import load_targets
        targets = load_targets(path)
        assert targets == []
    finally:
        os.unlink(path)
