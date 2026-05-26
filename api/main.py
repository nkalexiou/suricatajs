from fastapi import FastAPI
from api.routers import alerts, health


def create_app() -> FastAPI:
    app = FastAPI(
        title="SuricataJS",
        version="2.0.0",
        description="JavaScript integrity monitoring API",
    )
    app.include_router(health.router)
    app.include_router(alerts.router)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8085)
