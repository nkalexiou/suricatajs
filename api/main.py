import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from api.routers import alerts, auth, domains, health, metrics, targets, users
from db.database import init_db

logger = logging.getLogger("suricatajs")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    global_interval = int(os.getenv("SCAN_INTERVAL_MINUTES", "60"))
    scheduler = None
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from scanner.engine import check_target
        from scanner.loader import load_targets

        scheduler = BackgroundScheduler()
        existing_targets = load_targets()
        for t in existing_targets:
            interval = t.get("scan_interval_minutes") or global_interval
            try:
                scheduler.add_job(
                    check_target,
                    "interval",
                    minutes=interval,
                    args=[t],
                    id=f"scan_{t['url']}",
                    replace_existing=True,
                )
            except Exception:
                logger.exception(f"Failed to schedule {t['url']}")
        scheduler.start()
        logger.info(f"Interval scanner started with {len(existing_targets)} target(s).")
    except Exception:
        logger.exception("Failed to start background scheduler — interval scanning disabled.")

    app.state.scheduler = scheduler
    app.state.scan_interval = global_interval

    yield

    if scheduler is not None:
        try:
            scheduler.shutdown(wait=False)
        except Exception:
            pass


# Paths that exist in both the API and the SPA router.
# When a browser refreshes on these paths it sends Accept: text/html —
# we must serve index.html so the React router handles the route, not the API.
_SPA_OVERLAP_PATHS = frozenset({
    "/alerts", "/metrics", "/profile", "/login",
    "/admin/users",
})


def create_app() -> FastAPI:
    app = FastAPI(
        title="SuricataJS",
        version="2.0.0",
        description="JavaScript integrity monitoring API",
        lifespan=lifespan,
    )

    ui_dist = os.path.join(os.path.dirname(__file__), "..", "ui", "dist")
    index_path = os.path.join(ui_dist, "index.html")

    @app.middleware("http")
    async def spa_browser_fallback(request: Request, call_next):
        """Return index.html for browser page-refreshes on SPA routes."""
        path = request.url.path
        accept = request.headers.get("accept", "")
        is_browser = "text/html" in accept
        is_spa_path = path in _SPA_OVERLAP_PATHS or path.startswith("/domains/")
        if request.method == "GET" and is_browser and is_spa_path and os.path.isfile(index_path):
            return FileResponse(index_path)
        return await call_next(request)

    # API routers — registered after middleware so API paths still resolve for
    # non-browser clients (Prometheus, curl, fetch()).
    app.include_router(health.router)
    app.include_router(metrics.router)
    app.include_router(auth.router)
    app.include_router(alerts.router)
    app.include_router(targets.router)
    app.include_router(users.router)
    app.include_router(domains.router)

    # SPA static files — serves assets (JS/CSS) and index.html for /
    if os.path.isdir(ui_dist):
        app.mount("/", StaticFiles(directory=ui_dist, html=True), name="ui")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8085)
