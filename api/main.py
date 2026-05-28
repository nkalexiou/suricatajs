from contextlib import asynccontextmanager
from fastapi import FastAPI
from api.routers import alerts, health, metrics, targets
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
    app.include_router(health.router)
    app.include_router(metrics.router)
    app.include_router(alerts.router)
    app.include_router(targets.router)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8085)
