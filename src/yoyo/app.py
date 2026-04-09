from fastapi import FastAPI

from yoyo.api.router import api_router
from yoyo.core.config import get_settings
from yoyo.core.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="Yoyo API", version="0.1.0")
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
