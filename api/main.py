import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from api.routers import alerts, auth, domains, health, metrics, targets, users
from db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="SuricataJS",
        version="2.0.0",
        description="JavaScript integrity monitoring API",
        lifespan=lifespan,
    )
    # API routers — registered before StaticFiles so they take priority
    app.include_router(health.router)
    app.include_router(metrics.router)
    app.include_router(auth.router)
    app.include_router(alerts.router)
    app.include_router(targets.router)
    app.include_router(users.router)
    app.include_router(domains.router)

    # SPA — only mount if ui/dist exists (not present during tests or dev without build)
    ui_dist = os.path.join(os.path.dirname(__file__), "..", "ui", "dist")
    if os.path.isdir(ui_dist):
        app.mount("/", StaticFiles(directory=ui_dist, html=True), name="ui")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8085)
