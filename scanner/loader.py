import datetime
import json
import os
from typing import Dict, List

import yaml
from sqlalchemy import text

from db.database import get_connection


def _parse_txt(path: str) -> List[Dict]:
    targets = []
    with open(path) as f:
        for line in f:
            url = line.strip()
            if url and not url.startswith("#"):
                targets.append({"url": url})
    return targets


def _parse_yaml(path: str) -> List[Dict]:
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return data.get("targets", [])


def _import_to_db(targets: List[Dict]) -> None:
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for t in targets:
        try:
            with get_connection() as conn:
                conn.execute(
                    text("INSERT INTO targets (url, name, tags, owner, scan_interval_minutes, created_at) "
                         "VALUES (:url, :name, :tags, :owner, :interval, :created_at)"),
                    {
                        "url": t["url"],
                        "name": t.get("name"),
                        "tags": json.dumps(t["tags"]) if t.get("tags") else None,
                        "owner": t.get("owner"),
                        "interval": t.get("scan_interval_minutes"),
                        "created_at": now,
                    },
                )
        except Exception as e:
            if "UNIQUE" in str(e) or "unique" in str(e) or "duplicate" in str(e).lower():
                continue  # URL already exists; skip
            raise


def _rows_to_dicts(rows) -> List[Dict]:
    return [
        {
            "id": r[0],
            "url": r[1],
            "name": r[2],
            "tags": json.loads(r[3]) if r[3] else None,
            "owner": r[4],
            "scan_interval_minutes": r[5],
            "approved_checksum": r[6],
        }
        for r in rows
    ]


def load_targets(targets_file: str = "targets.txt") -> List[Dict]:
    """Load targets from DB. If DB is empty and file exists, import file into DB first."""
    with get_connection() as conn:
        rows = conn.execute(
            text("SELECT id, url, name, tags, owner, scan_interval_minutes, approved_checksum "
                 "FROM targets")
        ).fetchall()

    if rows:
        return _rows_to_dicts(rows)

    if not os.path.exists(targets_file):
        return []

    if targets_file.endswith((".yaml", ".yml")):
        file_targets = _parse_yaml(targets_file)
    else:
        file_targets = _parse_txt(targets_file)

    if not file_targets:
        return []

    _import_to_db(file_targets)

    with get_connection() as conn:
        rows = conn.execute(
            text("SELECT id, url, name, tags, owner, scan_interval_minutes, approved_checksum "
                 "FROM targets")
        ).fetchall()
    return _rows_to_dicts(rows)
