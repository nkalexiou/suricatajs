import datetime
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from api.auth import get_current_user, require_any_auth
from api.models import AlertResponse, DiffResponse
from db.database import get_connection

logger = logging.getLogger("suricatajs")
router = APIRouter(prefix="/alerts", dependencies=[Depends(require_any_auth)])

_SELECT = ("SELECT id, javascript, stored_checksum, new_checksum, date, alert_msg, "
           "alert_type, diff, sri, resolved, resolved_at, resolved_by, source_page FROM alerts")


def _row_to_alert(r) -> AlertResponse:
    return AlertResponse(
        id=r[0], javascript=r[1], stored_checksum=r[2], new_checksum=r[3],
        date=r[4], alert_msg=r[5], alert_type=r[6], diff=r[7], sri=r[8],
        resolved=bool(r[9]), resolved_at=r[10], resolved_by=r[11],
        source_page=r[12],
    )


@router.get("", response_model=List[AlertResponse])
def get_alerts(
    type: Optional[str] = Query(None),
    javascript: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    resolved: Optional[int] = Query(None, description="0=open, 1=resolved, omit=open only"),
):
    query = _SELECT
    conditions, params = [], {}

    # Default: show open only; pass resolved=1 for resolved, resolved=0 explicit for open
    if resolved is None:
        conditions.append("resolved = 0")
    else:
        conditions.append("resolved = :resolved")
        params["resolved"] = resolved

    if type:
        conditions.append("alert_type = :type")
        params["type"] = type
    if javascript:
        conditions.append("javascript = :javascript")
        params["javascript"] = javascript
    if date:
        conditions.append("date = :date")
        params["date"] = date

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    with get_connection() as conn:
        rows = conn.execute(text(query), params).fetchall()
    return [_row_to_alert(r) for r in rows]


@router.get("/{alert_id}/diff", response_model=DiffResponse)
def get_alert_diff(alert_id: int):
    with get_connection() as conn:
        row = conn.execute(
            text("SELECT id, diff FROM alerts WHERE id = :id"), {"id": alert_id}
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")
    if not row[1]:
        raise HTTPException(status_code=404, detail="No diff available for this alert")
    return DiffResponse(alert_id=row[0], diff=row[1])


@router.patch("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(alert_id: int, current_user: dict = Depends(get_current_user)):
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    with get_connection() as conn:
        row = conn.execute(
            text("SELECT id FROM alerts WHERE id = :id"), {"id": alert_id}
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Alert not found")
        conn.execute(
            text("UPDATE alerts SET resolved=1, resolved_at=:now, resolved_by=:uid WHERE id=:id"),
            {"now": now, "uid": current_user["id"], "id": alert_id},
        )
        updated = conn.execute(text(_SELECT + " WHERE id = :id"), {"id": alert_id}).fetchone()
    return _row_to_alert(updated)


@router.patch("/{alert_id}/approve", response_model=AlertResponse)
def approve_alert(alert_id: int, current_user: dict = Depends(get_current_user)):
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    with get_connection() as conn:
        row = conn.execute(
            text("SELECT id, javascript, new_checksum FROM alerts WHERE id = :id"),
            {"id": alert_id},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Alert not found")
        script_uri, new_checksum = row[1], row[2]
        if not new_checksum:
            raise HTTPException(status_code=400, detail="Alert has no new checksum to approve")
        conn.execute(
            text("UPDATE suricatajs SET checksum = :checksum WHERE uri = :uri"),
            {"checksum": new_checksum, "uri": script_uri},
        )
        conn.execute(
            text("UPDATE alerts SET resolved=1, resolved_at=:now, resolved_by=:uid WHERE id=:id"),
            {"now": now, "uid": current_user["id"], "id": alert_id},
        )
        updated = conn.execute(text(_SELECT + " WHERE id = :id"), {"id": alert_id}).fetchone()
    return _row_to_alert(updated)
