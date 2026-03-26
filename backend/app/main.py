import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler

from app.config import settings
from app.db.database import init_db
from app.middleware.logging import RequestLoggingMiddleware, configure_logging
from app.routers.chat import router as chat_router
from app.routers.feedback_router import router as feedback_router
from app.routers.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(title="CSS Prep AI API", version="1.0.0", lifespan=lifespan)
    app.state.started_at = time.monotonic()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.limiter = settings.limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(feedback_router)

    return app


app = create_app()
