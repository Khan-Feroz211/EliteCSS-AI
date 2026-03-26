import logging
import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


def configure_logging() -> None:
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(level=logging.INFO, format="%(message)s")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger = structlog.get_logger("http")
        start = time.perf_counter()

        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        user_id = request.headers.get("x-user-id", "anonymous")
        model = "unknown"

        if request.method == "POST" and "application/json" in request.headers.get(
            "content-type", ""
        ):
            body = await request.body()
            if body:
                try:
                    import json

                    payload = json.loads(body)
                    model = payload.get("model", "unknown")
                except Exception:
                    model = "unknown"

            async def receive():
                return {"type": "http.request", "body": body, "more_body": False}

            request._receive = receive

        response = await call_next(request)
        latency_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "request_completed",
            request_id=request_id,
            user_id=user_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            latency_ms=round(latency_ms, 2),
            model=model,
            token_count=0,
        )

        response.headers["x-request-id"] = request_id
        return response
