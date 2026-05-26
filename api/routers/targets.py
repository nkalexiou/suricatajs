import datetime
import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import text

from api.auth import require_api_key
from api.models import ApproveRequest, TargetCreate, TargetResponse
from db.database import get_connection

router = APIRouter(prefix="/targets", dependencies=[Depends(require_api_key)])


def _row_to_target(r) -> TargetResponse:
    return TargetResponse(
        id=r[0],
        url=r[1],
        name=r[2],
        tags=json.loads(r[3]) if r[3] else None,
        owner=r[4],
        scan_interval_minutes=r[5],
        approved_checksum=r[6],
        approval_note=r[7],
        approved_at=r[8],
        created_at=r[9],
    )


@router.get("", response_model=List[TargetResponse])
def list_targets():
    with get_connection() as conn:
        rows = conn.execute(
            text("SELECT id, url, name, tags, owner, scan_interval_minutes, "
                 "approved_checksum, approval_note, approved_at, created_at FROM targets")
        ).fetchall()
    return [_row_to_target(r) for r in rows]


@router.post("", response_model=TargetResponse, status_code=201)
def create_target(body: TargetCreate):
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    tags_json = json.dumps(body.tags) if body.tags else None
    try:
        with get_connection() as conn:
            conn.execute(
                text("INSERT INTO targets (url, name, tags, owner, scan_interval_minutes, created_at) "
                     "VALUES (:url, :name, :tags, :owner, :interval, :created_at)"),
                {
                    "url": body.url,
                    "name": body.name,
                    "tags": tags_json,
                    "owner": body.owner,
                    "interval": body.scan_interval_minutes,
                    "created_at": now,
                },
            )
            row = conn.execute(
                text("SELECT id, url, name, tags, owner, scan_interval_minutes, "
                     "approved_checksum, approval_note, approved_at, created_at "
                     "FROM targets WHERE url = :url"),
                {"url": body.url},
            ).fetchone()
    except Exception as e:
        if "UNIQUE" in str(e) or "unique" in str(e) or "duplicate" in str(e).lower():
            raise HTTPException(status_code=409, detail="Target URL already exists")
        raise
    return _row_to_target(row)


@router.delete("/{target_id}", status_code=204)
def delete_target(target_id: int):
    with get_connection() as conn:
        result = conn.execute(
            text("DELETE FROM targets WHERE id = :id"), {"id": target_id}
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Target not found")
    return Response(status_code=204)


@router.post("/{target_id}/approve", response_model=TargetResponse)
def approve_target(target_id: int, body: ApproveRequest):
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    with get_connection() as conn:
        target_row = conn.execute(
            text("SELECT id, url FROM targets WHERE id = :id"), {"id": target_id}
        ).fetchone()
        if not target_row:
            raise HTTPException(status_code=404, detail="Target not found")

        page_url = target_row[1]
        checksum_row = conn.execute(
            text("SELECT checksum FROM suricatajs WHERE uri LIKE :prefix "
                 "ORDER BY date DESC LIMIT 1"),
            {"prefix": f"{page_url}%"},
        ).fetchone()
        approved_checksum = checksum_row[0] if checksum_row else None

        conn.execute(
            text("UPDATE targets SET approved_checksum = :checksum, "
                 "approval_note = :note, approved_at = :approved_at WHERE id = :id"),
            {
                "checksum": approved_checksum,
                "note": body.note,
                "approved_at": now,
                "id": target_id,
            },
        )
        row = conn.execute(
            text("SELECT id, url, name, tags, owner, scan_interval_minutes, "
                 "approved_checksum, approval_note, approved_at, created_at "
                 "FROM targets WHERE id = :id"),
            {"id": target_id},
        ).fetchone()
    return _row_to_target(row)
