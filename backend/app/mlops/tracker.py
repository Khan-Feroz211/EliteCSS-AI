from app.mlops.logger import get_logger
from app.mlops.mlflow_tracker import _safe_mlflow_setup, track_llm_call  # noqa: F401

logger = get_logger(__name__)


def setup_mlflow() -> None:
    """
    Configure MLflow to point at the tracking server.
    Called once at application startup in lifespan.
    """
    try:
        _safe_mlflow_setup()
        from app.config import get_settings
        settings = get_settings()
        logger.info(
            "MLflow configured",
            extra={"endpoint": settings.mlflow_tracking_uri},
        )
    except Exception as exc:
        logger.warning("MLflow setup failed", extra={"message": str(exc)})
