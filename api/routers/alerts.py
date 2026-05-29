from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from api.auth import require_any_auth
from api.models import AlertResponse, DiffResponse
from db.database import get_connection

router = APIRouter(prefix="/alerts", dependencies=[Depends(require_any_auth)])


@router.get("", response_model=List[AlertResponse])
def get_alerts(
    type: Optional[str] = Query(None),
    javascript: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
):
    query = ("SELECT id, javascript, stored_checksum, new_checksum, date, alert_msg, alert_type, diff, sri "
             "FROM alerts")
    conditions, params = [], {}

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

    return [
        AlertResponse(
            id=r[0],
            javascript=r[1],
            stored_checksum=r[2],
            new_checksum=r[3],
            date=r[4],
            alert_msg=r[5],
            alert_type=r[6],
            diff=r[7],
            sri=r[8],
        )
        for r in rows
    ]


@router.get("/{alert_id}/diff", response_model=DiffResponse)
def get_alert_diff(alert_id: int):
    with get_connection() as conn:
        row = conn.execute(
            text("SELECT id, diff FROM alerts WHERE id = :id"),
            {"id": alert_id},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")
    if not row[1]:
        raise HTTPException(status_code=404, detail="No diff available for this alert")
    return DiffResponse(alert_id=row[0], diff=row[1])
