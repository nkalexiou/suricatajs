import datetime
from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import CollectorRegistry, Gauge, generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy import text
from db.database import get_connection

router = APIRouter()


@router.get("/metrics", include_in_schema=False)
def metrics():
    registry = CollectorRegistry()

    with get_connection() as conn:
        alert_rows = conn.execute(
            text("SELECT alert_type, COUNT(*) FROM alerts GROUP BY alert_type")
        ).fetchall()
        scripts_total = conn.execute(
            text("SELECT COUNT(DISTINCT uri) FROM suricatajs")
        ).fetchone()[0] or 0
        targets_total = conn.execute(
            text("SELECT COUNT(*) FROM targets")
        ).fetchone()[0] or 0
        last_date_row = conn.execute(
            text("SELECT date FROM suricatajs ORDER BY date DESC LIMIT 1")
        ).fetchone()

    alerts_gauge = Gauge(
        "suricatajs_alerts_total", "Total alerts by type", ["alert_type"], registry=registry
    )
    for alert_type, count in alert_rows:
        alerts_gauge.labels(alert_type=alert_type).set(count)

    Gauge("suricatajs_scripts_total", "Total distinct scripts tracked", registry=registry).set(scripts_total)
    Gauge("suricatajs_targets_total", "Total targets", registry=registry).set(targets_total)

    last_scan_ts = 0.0
    if last_date_row:
        try:
            dt = datetime.datetime.strptime(last_date_row[0], "%Y%m%d_%H%M%S")
            last_scan_ts = dt.timestamp()
        except ValueError:
            pass
    Gauge(
        "suricatajs_last_scan_timestamp_seconds",
        "Unix timestamp of the most recent script scan",
        registry=registry,
    ).set(last_scan_ts)

    return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)
