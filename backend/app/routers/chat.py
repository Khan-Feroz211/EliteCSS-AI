import json
import time
import uuid
from collections.abc import Iterator

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse

from app.config import settings
from app.mlops.mlflow_tracker import clear_tracking_context, set_tracking_context
from app.mlops.prompt_manager import detect_exam_topic, load_prompt, select_prompt_version
from app.mlops.quality_monitor import analyze_response
from app.models.schemas import ChatRequest, ChatResponse
from app.services.claude import call_claude, stream_claude
from app.services.gemini import call_gemini, stream_gemini
from app.services.gpt import call_gpt, stream_gpt

router = APIRouter(prefix="/api/v1", tags=["chat"])
logger = structlog.get_logger("chat")


def get_user_id(x_user_id: str | None = Header(default=None)) -> str:
    return x_user_id or "anonymous"


def get_session_id(x_session_id: str | None = Header(default=None)) -> str:
    return x_session_id or "default"


def _resolve_model_name(model: str) -> str:
    if model == "gpt":
        return settings.openai_model
    if model == "claude":
        return settings.claude_model
    if model == "gemini":
        return settings.gemini_model
    raise HTTPException(status_code=400, detail="Invalid model selected")


def _chat_call(model: str, messages: list[dict[str, str]], system_prompt: str) -> tuple[str, int]:
    if model == "gpt":
        return call_gpt(messages, system_prompt=system_prompt)
    if model == "claude":
        return call_claude(messages, system_prompt=system_prompt)
    if model == "gemini":
        return call_gemini(messages, system_prompt=system_prompt)
    raise HTTPException(status_code=400, detail="Invalid model selected")


def _stream_call(model: str, messages: list[dict[str, str]], system_prompt: str) -> Iterator[str]:
    if model == "gpt":
        return stream_gpt(messages, system_prompt=system_prompt)
    if model == "claude":
        return stream_claude(messages, system_prompt=system_prompt)
    if model == "gemini":
        return stream_gemini(messages, system_prompt=system_prompt)
    raise HTTPException(status_code=400, detail="Invalid model selected")


@router.post("/chat", response_model=ChatResponse)
@settings.limiter.limit(settings.rate_limit)
def chat(
    request: Request,
    response: Response,
    payload: ChatRequest,
    user_id: str = Depends(get_user_id),
    session_id: str = Depends(get_session_id),
) -> ChatResponse:
    del request

    messages = [m.model_dump() for m in payload.messages]
    model_name = _resolve_model_name(payload.model)
    prompt_version = select_prompt_version()
    system_prompt = load_prompt(prompt_version)
    exam_topic = detect_exam_topic(messages)
    message_id = uuid.uuid4().hex
    response.headers["x-message-id"] = message_id

    set_tracking_context(
        user_id=user_id,
        session_id=session_id,
        exam_topic=exam_topic,
        prompt_version=prompt_version,
        message_id=message_id,
    )

    started = time.perf_counter()

    try:
        reply, tokens_used = _chat_call(payload.model, messages, system_prompt=system_prompt)
    except Exception as exc:
        logger.exception(
            "chat_failed",
            model=model_name,
            user_id=user_id,
            token_count=0,
            latency_ms=(time.perf_counter() - started) * 1000,
            error=str(exc),
            session_id=session_id,
        )
        clear_tracking_context()
        raise HTTPException(status_code=502, detail="Model provider call failed") from exc

    latency_ms = (time.perf_counter() - started) * 1000
    quality_metrics = analyze_response(reply, latency_ms)

    logger.info(
        "chat_completed",
        model=model_name,
        user_id=user_id,
        session_id=session_id,
        message_id=message_id,
        prompt_version=prompt_version,
        exam_topic=exam_topic,
        token_count=tokens_used,
        latency_ms=latency_ms,
        response_relevance_score=quality_metrics["response_relevance_score"],
        response_length_chars=quality_metrics["response_length_chars"],
        model_latency_p50_p95_p99=quality_metrics["model_latency_p50_p95_p99"],
    )

    clear_tracking_context()

    return ChatResponse(
        reply=reply,
        model=model_name,
        tokens_used=tokens_used,
        latency_ms=round(latency_ms, 2),
    )


@router.post("/chat/stream")
@settings.limiter.limit(settings.rate_limit)
def chat_stream(
    request: Request,
    payload: ChatRequest,
    user_id: str = Depends(get_user_id),
    session_id: str = Depends(get_session_id),
) -> StreamingResponse:
    del request

    messages = [m.model_dump() for m in payload.messages]
    model_name = _resolve_model_name(payload.model)
    prompt_version = select_prompt_version()
    system_prompt = load_prompt(prompt_version)
    exam_topic = detect_exam_topic(messages)
    message_id = uuid.uuid4().hex

    set_tracking_context(
        user_id=user_id,
        session_id=session_id,
        exam_topic=exam_topic,
        prompt_version=prompt_version,
        message_id=message_id,
    )

    started = time.perf_counter()

    def event_generator() -> Iterator[str]:
        token_count = 0
        try:
            meta = json.dumps({"message_id": message_id, "prompt_version": prompt_version, "model": model_name})
            yield f"event: meta\ndata: {meta}\n\n"

            for token in _stream_call(payload.model, messages, system_prompt=system_prompt):
                token_count += 1
                chunk = json.dumps({"token": token, "model": model_name})
                yield f"event: token\ndata: {chunk}\n\n"

            latency_ms = (time.perf_counter() - started) * 1000
            done = json.dumps(
                {
                    "done": True,
                    "model": model_name,
                    "latency_ms": round(latency_ms, 2),
                    "message_id": message_id,
                    "prompt_version": prompt_version,
                }
            )
            yield f"event: done\ndata: {done}\n\n"

            logger.info(
                "chat_stream_completed",
                model=model_name,
                user_id=user_id,
                session_id=session_id,
                message_id=message_id,
                prompt_version=prompt_version,
                exam_topic=exam_topic,
                token_count=token_count,
                latency_ms=latency_ms,
            )
            clear_tracking_context()
        except Exception as exc:
            logger.exception(
                "chat_stream_failed",
                model=model_name,
                user_id=user_id,
                session_id=session_id,
                message_id=message_id,
                token_count=token_count,
                latency_ms=(time.perf_counter() - started) * 1000,
                error=str(exc),
            )
            err = json.dumps({"error": "Model provider call failed"})
            yield f"event: error\ndata: {err}\n\n"
            clear_tracking_context()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/chat/stream")
@settings.limiter.limit(settings.rate_limit)
def chat_stream_eventsource(
    request: Request,
    messages: str = Query(..., description="JSON-encoded chat messages"),
    model: str = Query("gpt", pattern="^(gpt|claude|gemini)$"),
    user_id: str = Query("anonymous"),
    session_id: str = Query("default"),
) -> StreamingResponse:
    payload = ChatRequest.model_validate({"messages": json.loads(messages), "model": model})
    return chat_stream(request=request, payload=payload, user_id=user_id, session_id=session_id)
