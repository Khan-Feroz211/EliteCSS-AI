import json
import hashlib
import time
import uuid
from collections.abc import AsyncIterator
from collections import OrderedDict

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db as get_db_dep
from app.db.models import User
from app.dependencies import get_current_user
from app.mlops.mlflow_tracker import clear_tracking_context, set_tracking_context
from app.mlops.prompt_manager import (
    detect_exam_topic,
    load_prompt,
    select_prompt_version,
)
from app.mlops.quality_monitor import analyze_response
from app.models.schemas import ChatRequest, ChatResponse, StreamRequest
from app.services.auth import decode_access_token
from app.services.claude import call_claude, stream_claude
from app.services.gemini import call_gemini, stream_gemini
from app.services.gpt import call_gpt, stream_gpt

router = APIRouter(prefix="/api/v1", tags=["chat"])
logger = structlog.get_logger("chat")
_RESPONSE_CACHE: OrderedDict[str, tuple[float, str, int]] = OrderedDict()


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


async def _chat_call(
    model: str, messages: list[dict[str, str]], system_prompt: str
) -> tuple[str, int]:
    if model == "gpt":
        return await call_gpt(messages, system_prompt=system_prompt)
    if model == "claude":
        return await call_claude(messages, system_prompt=system_prompt)
    if model == "gemini":
        return await call_gemini(messages, system_prompt=system_prompt)
    raise HTTPException(status_code=400, detail="Invalid model selected")


async def _stream_call(
    model: str, messages: list[dict[str, str]], system_prompt: str
) -> AsyncIterator[str]:
    if model == "gpt":
        async for token in stream_gpt(messages, system_prompt=system_prompt):
            yield token
    elif model == "claude":
        async for token in stream_claude(messages, system_prompt=system_prompt):
            yield token
    elif model == "gemini":
        async for token in stream_gemini(messages, system_prompt=system_prompt):
            yield token
    else:
        raise HTTPException(status_code=400, detail="Invalid model selected")


def _optimize_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    max_history = max(int(settings.max_history_messages), 1)
    if len(messages) <= max_history:
        return messages
    return messages[-max_history:]


def _cache_key(model: str, messages: list[dict[str, str]], prompt_version: str) -> str:
    payload = json.dumps(
        {"model": model, "prompt_version": prompt_version, "messages": messages},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_get(cache_key: str) -> tuple[str, int] | None:
    if not settings.enable_response_cache:
        return None

    entry = _RESPONSE_CACHE.get(cache_key)
    if entry is None:
        return None

    expires_at, reply, tokens_used = entry
    if expires_at <= time.time():
        _RESPONSE_CACHE.pop(cache_key, None)
        return None

    _RESPONSE_CACHE.move_to_end(cache_key)
    return reply, tokens_used


def _cache_set(cache_key: str, reply: str, tokens_used: int) -> None:
    if not settings.enable_response_cache:
        return

    ttl_seconds = max(int(settings.response_cache_ttl_seconds), 0)
    max_entries = max(int(settings.response_cache_max_entries), 1)
    if ttl_seconds == 0:
        return

    _RESPONSE_CACHE[cache_key] = (time.time() + ttl_seconds, reply, tokens_used)
    _RESPONSE_CACHE.move_to_end(cache_key)

    while len(_RESPONSE_CACHE) > max_entries:
        _RESPONSE_CACHE.popitem(last=False)


@router.post("/chat", response_model=ChatResponse)
@settings.limiter.limit(settings.rate_limit)
async def chat(
    request: Request,
    response: Response,
    payload: ChatRequest,
    user_id: str = Depends(get_user_id),
    session_id: str = Depends(get_session_id),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    del request

    logger.info("chat_request", user_id=current_user.id, model=payload.model)
    started = time.perf_counter()
    messages = _optimize_messages([m.model_dump() for m in payload.messages])
    model_name = _resolve_model_name(payload.model)
    prompt_version = select_prompt_version()
    system_prompt = load_prompt(prompt_version)
    exam_topic = detect_exam_topic(messages)
    message_id = uuid.uuid4().hex
    response.headers["x-message-id"] = message_id
    cache_key = _cache_key(payload.model, messages, prompt_version)

    cached = _cache_get(cache_key)
    if cached is not None:
        cached_reply, _ = cached
        latency_ms = (time.perf_counter() - started) * 1000
        response.headers["x-cache"] = "hit"
        logger.info(
            "chat_cache_hit",
            model=model_name,
            user_id=user_id,
            session_id=session_id,
            message_id=message_id,
            prompt_version=prompt_version,
            exam_topic=exam_topic,
            latency_ms=latency_ms,
        )
        return ChatResponse(
            reply=cached_reply,
            model=model_name,
            tokens_used=0,
            latency_ms=round(latency_ms, 2),
        )

    set_tracking_context(
        user_id=user_id,
        session_id=session_id,
        exam_topic=exam_topic,
        prompt_version=prompt_version,
        message_id=message_id,
    )
    response.headers["x-cache"] = "miss"

    try:
        reply, tokens_used = await _chat_call(
            payload.model, messages, system_prompt=system_prompt
        )
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
        raise HTTPException(
            status_code=502, detail="Model provider call failed"
        ) from exc

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
    _cache_set(cache_key, reply, tokens_used)

    clear_tracking_context()

    return ChatResponse(
        reply=reply,
        model=model_name,
        tokens_used=tokens_used,
        latency_ms=round(latency_ms, 2),
    )


@router.post("/chat/stream")
@settings.limiter.limit(settings.rate_limit)
async def chat_stream(
    request: Request,
    payload: StreamRequest,
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    SSE streaming endpoint. Returns text/event-stream response.
    Each chunk is formatted as SSE: "data: {text}\\n\\n"
    A final "data: [DONE]\\n\\n" signals the stream is complete.
    """
    del request

    messages = _optimize_messages(
        [*[m.model_dump() for m in payload.history], {"role": "user", "content": payload.message}]
    )
    system_prompt = load_prompt(select_prompt_version())

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for token in _stream_call(payload.model, messages, system_prompt=system_prompt):
                safe = token.replace("\n", "\\n")
                yield f"data: {safe}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            yield f"data: [ERROR] {str(exc)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chat/stream")
@settings.limiter.limit(settings.rate_limit)
async def chat_stream_eventsource(
    request: Request,
    messages: str = Query(..., description="JSON-encoded chat messages"),
    model: str = Query("gpt", pattern="^(gpt|claude|gemini)$"),
    user_id: str = Query("anonymous"),
    session_id: str = Query("default"),
    token: str = Query(..., description="Bearer token for authentication"),
    db: AsyncSession = Depends(get_db_dep),
) -> StreamingResponse:
    del request, user_id, session_id
    token_data = decode_access_token(token)
    result = await db.execute(select(User).where(User.id == token_data.user_id))
    current_user = result.scalar_one_or_none()
    if current_user is None or not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    optimized = _optimize_messages(json.loads(messages))
    system_prompt = load_prompt(select_prompt_version())

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for token_text in _stream_call(model, optimized, system_prompt=system_prompt):
                safe = token_text.replace("\n", "\\n")
                yield f"data: {safe}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            yield f"data: [ERROR] {str(exc)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
