import datetime
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import text

from api.auth import get_current_user
from api.models import DomainCreate, DomainResponse
from db.database import get_connection

logger = logging.getLogger("suricatajs")
router = APIRouter(prefix="/domains", dependencies=[Depends(get_current_user)])


@router.get("", response_model=List[DomainResponse])
def list_domains():
    with get_connection() as conn:
        rows = conn.execute(
            text("SELECT id, domain, created_at FROM domains ORDER BY domain")
        ).fetchall()
    return [DomainResponse(id=r[0], domain=r[1], created_at=r[2]) for r in rows]


@router.post("", response_model=DomainResponse, status_code=201)
def create_domain(body: DomainCreate):
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    try:
        with get_connection() as conn:
            result = conn.execute(
                text("INSERT INTO domains (domain, created_at) VALUES (:domain, :now)"),
                {"domain": body.domain.strip().lower(), "now": now},
            )
            new_id = result.lastrowid
            row = conn.execute(
                text("SELECT id, domain, created_at FROM domains WHERE id = :id"),
                {"id": new_id},
            ).fetchone()
    except Exception as e:
        if "UNIQUE" in str(e) or "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail="Domain already exists")
        raise
    return DomainResponse(id=row[0], domain=row[1], created_at=row[2])


@router.delete("/{domain_id}", status_code=204)
def delete_domain(domain_id: int):
    with get_connection() as conn:
        row = conn.execute(
            text("SELECT id FROM domains WHERE id = :id"), {"id": domain_id}
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Domain not found")
        target_count = conn.execute(
            text("SELECT COUNT(*) FROM targets WHERE domain_id = :id"), {"id": domain_id}
        ).scalar()
        if target_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete domain: {target_count} targets are assigned to it"
            )
        conn.execute(text("DELETE FROM domains WHERE id = :id"), {"id": domain_id})
    return Response(status_code=204)
