import time

from fastapi import APIRouter, Request

from app.config import settings
from app.models.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    uptime = time.monotonic() - request.app.state.started_at
    return HealthResponse(
        status="ok",
        uptime=round(uptime, 2),
        models_available=[
            settings.openai_model,
            settings.claude_model,
            settings.gemini_model,
        ],
        mlflow_tracking="enabled",
        metrics_endpoint="/metrics",
    )
