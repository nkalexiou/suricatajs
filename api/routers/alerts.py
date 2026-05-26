from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from api.auth import require_api_key
from api.models import AlertResponse
from db.database import get_connection

router = APIRouter(prefix="/alerts", dependencies=[Depends(require_api_key)])


@router.get("", response_model=List[AlertResponse])
def get_alerts(
    type: Optional[str] = Query(None),
    javascript: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
):
    query = ("SELECT id, javascript, stored_checksum, new_checksum, date, alert_msg, alert_type, diff "
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
        )
        for r in rows
    ]
