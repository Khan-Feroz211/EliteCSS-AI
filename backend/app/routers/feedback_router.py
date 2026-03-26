import structlog
from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db
from app.db.models import Feedback
from app.mlops.mlflow_tracker import get_run_id
from app.models.schemas import FeedbackRequest, FeedbackResponse

router = APIRouter(prefix="/api/v1", tags=["feedback"])
logger = structlog.get_logger("feedback")


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    payload: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    x_user_id: str | None = Header(default=None),
    x_session_id: str | None = Header(default=None),
) -> FeedbackResponse:
    user_id = x_user_id or "anonymous"
    session_id = x_session_id or "default"

    entity = Feedback(
        message_id=payload.message_id,
        rating=payload.rating,
        comment=payload.comment,
        user_id=user_id,
        session_id=session_id,
    )
    db.add(entity)
    await db.commit()
    await db.refresh(entity)

    run_id = get_run_id(payload.message_id)
    if run_id:
        try:
            import mlflow

            mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
            mlflow.set_experiment(settings.mlflow_experiment_name)
            with mlflow.start_run(run_id=run_id):
                mlflow.log_metric("feedback_rating", float(payload.rating))
                if payload.comment:
                    mlflow.set_tag("feedback_comment", payload.comment)
        except Exception as exc:
            logger.warning("feedback_mlflow_link_failed", message_id=payload.message_id, error=str(exc))

    logger.info(
        "feedback_recorded",
        message_id=payload.message_id,
        user_id=user_id,
        session_id=session_id,
        rating=payload.rating,
    )

    return FeedbackResponse(status="stored", feedback_id=entity.id, linked_to_run=bool(run_id))
