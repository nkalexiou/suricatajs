import datetime
import json
import logging
from typing import List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response
from sqlalchemy import text

from api.auth import require_any_auth
from api.models import ApproveRequest, TargetCreate, TargetResponse
from db.database import get_connection

logger = logging.getLogger("suricatajs")

router = APIRouter(prefix="/targets", dependencies=[Depends(require_any_auth)])

_TARGET_SELECT = ("SELECT id, url, name, tags, owner, scan_interval_minutes, "
                  "approved_checksum, approval_note, approved_at, created_at, "
                  "crawl_depth, use_playwright, domain_id, last_scanned_at FROM targets")


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
        crawl_depth=r[10] if r[10] is not None else 0,
        use_playwright=bool(r[11]) if r[11] is not None else False,
        domain_id=r[12],
        last_scanned_at=r[13],
    )


@router.get("", response_model=List[TargetResponse])
def list_targets(domain_id: Optional[int] = Query(None)):
    query = _TARGET_SELECT
    params = {}
    if domain_id is not None:
        query += " WHERE domain_id = :domain_id"
        params["domain_id"] = domain_id
    with get_connection() as conn:
        rows = conn.execute(text(query), params).fetchall()
    return [_row_to_target(r) for r in rows]


@router.post("", response_model=TargetResponse, status_code=201)
def create_target(body: TargetCreate, background_tasks: BackgroundTasks, request: Request):
    parsed = urlparse(body.url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(status_code=422, detail="Target URL must use http or https scheme")
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    tags_json = json.dumps(body.tags) if body.tags else None
    crawl_depth = body.crawl_depth if body.crawl_depth is not None else 0
    use_playwright = bool(body.use_playwright)
    try:
        with get_connection() as conn:
            result = conn.execute(
                text("INSERT INTO targets (url, name, tags, owner, scan_interval_minutes, "
                     "crawl_depth, use_playwright, domain_id, created_at) "
                     "VALUES (:url, :name, :tags, :owner, :interval, :crawl_depth, :use_playwright, :domain_id, :created_at)"),
                {
                    "url": body.url,
                    "name": body.name,
                    "tags": tags_json,
                    "owner": body.owner,
                    "interval": body.scan_interval_minutes,
                    "crawl_depth": crawl_depth,
                    "use_playwright": 1 if use_playwright else 0,
                    "domain_id": body.domain_id,
                    "created_at": now,
                },
            )
            new_id = result.lastrowid
            row = conn.execute(
                text(_TARGET_SELECT + " WHERE id = :id"),
                {"id": new_id},
            ).fetchone()
    except Exception as e:
        if "UNIQUE" in str(e) or "unique" in str(e) or "duplicate" in str(e).lower():
            raise HTTPException(status_code=409, detail="Target URL already exists")
        raise
    if row is None:
        raise HTTPException(status_code=500, detail="Target created but could not be retrieved")

    target_dict = {"url": body.url, "crawl_depth": crawl_depth, "use_playwright": use_playwright}

    # Trigger an immediate scan in the background
    try:
        from scanner.engine import check_target
        background_tasks.add_task(check_target, target_dict)
    except Exception:
        logger.exception(f"Failed to queue immediate scan for {body.url}")

    # Register an interval job in the running scheduler
    try:
        scheduler = request.app.state.scheduler
        if scheduler is not None:
            from scanner.engine import check_target
            global_interval = getattr(request.app.state, "scan_interval", 60)
            interval = body.scan_interval_minutes or global_interval
            scheduler.add_job(
                check_target,
                "interval",
                minutes=interval,
                args=[target_dict],
                id=f"scan_{body.url}",
                replace_existing=True,
            )
    except Exception:
        logger.exception(f"Failed to schedule interval scan for {body.url}")

    return _row_to_target(row)


@router.delete("/{target_id}", status_code=204)
def delete_target(target_id: int, request: Request):
    with get_connection() as conn:
        target_row = conn.execute(
            text("SELECT url FROM targets WHERE id = :id"), {"id": target_id}
        ).fetchone()
        result = conn.execute(
            text("DELETE FROM targets WHERE id = :id"), {"id": target_id}
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Target not found")

    if target_row:
        try:
            scheduler = request.app.state.scheduler
            if scheduler is not None:
                scheduler.remove_job(f"scan_{target_row[0]}")
        except Exception:
            pass  # Job may not exist (e.g. if scheduler was restarted)

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
        escaped_url = page_url.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        checksum_row = conn.execute(
            text("SELECT checksum FROM suricatajs WHERE uri LIKE :prefix ESCAPE '\\' "
                 "ORDER BY date DESC LIMIT 1"),
            {"prefix": f"{escaped_url}%"},
        ).fetchone()
        approved_checksum = checksum_row[0] if checksum_row else None
        if approved_checksum is None:
            logger.warning(
                f"Approving target {target_id} ({page_url}) with no prior scan data — "
                "approved_checksum will be null"
            )

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
            text(_TARGET_SELECT + " WHERE id = :id"),
            {"id": target_id},
        ).fetchone()
    return _row_to_target(row)
