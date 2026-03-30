from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.mlops.metrics import REGISTRY

router = APIRouter(tags=["monitoring"])


@router.get("/metrics")
async def metrics() -> Response:
    """
    Prometheus metrics endpoint.
    Prometheus scrapes this every 15 seconds.
    Do NOT add JWT protection — Prometheus needs unauthenticated access.
    In production, restrict this via nginx allow/deny rules.
    """
    data = generate_latest(REGISTRY)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
