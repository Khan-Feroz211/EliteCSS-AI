from __future__ import annotations

import asyncio
import contextvars
import functools
import threading
import time
from collections.abc import Callable
from typing import Any

from app.config import settings

_tracking_context: contextvars.ContextVar[dict[str, str]] = contextvars.ContextVar(
    "tracking_context", default={}
)
_run_registry_lock = threading.Lock()
_run_registry: dict[str, str] = {}


def set_tracking_context(**kwargs: str) -> None:
    current = dict(_tracking_context.get())
    current.update({k: v for k, v in kwargs.items() if v is not None})
    _tracking_context.set(current)


def clear_tracking_context() -> None:
    _tracking_context.set({})


def get_tracking_context() -> dict[str, str]:
    return dict(_tracking_context.get())


def register_run(message_id: str, run_id: str) -> None:
    with _run_registry_lock:
        _run_registry[message_id] = run_id


def get_run_id(message_id: str) -> str | None:
    with _run_registry_lock:
        return _run_registry.get(message_id)


def _safe_mlflow_setup() -> None:
    import mlflow

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment(settings.mlflow_experiment_name)


def _log_to_mlflow(
    model_name: str,
    context: dict[str, str],
    prompt_length: int,
    latency_ms: float,
    reply: str,
    tokens_used: int,
) -> None:
    try:
        import mlflow

        _safe_mlflow_setup()
        with mlflow.start_run(run_name=f"llm-{model_name}") as run:
            mlflow.log_params(
                {
                    "model_name": model_name,
                    "temperature": settings.temperature,
                    "max_tokens": settings.max_tokens,
                    "prompt_length": prompt_length,
                }
            )
            mlflow.log_metrics(
                {
                    "latency_ms": latency_ms,
                    "tokens_used": float(tokens_used),
                    "response_length": float(len(reply)),
                }
            )

            for key in [
                "user_id",
                "session_id",
                "exam_topic",
                "prompt_version",
                "message_id",
            ]:
                value = context.get(key)
                if value:
                    mlflow.set_tag(key, value)

            message_id = context.get("message_id")
            if message_id:
                register_run(message_id, run.info.run_id)
    except Exception:
        pass


def track_llm_call(
    model_name: str,
) -> Callable[[Callable[..., tuple[str, int]]], Callable[..., tuple[str, int]]]:
    def decorator(
        func: Callable[..., tuple[str, int]]
    ) -> Callable[..., tuple[str, int]]:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> tuple[str, int]:
                context = get_tracking_context()
                messages = args[0] if args else kwargs.get("messages", [])
                prompt_length = (
                    sum(len(m.get("content", "")) for m in messages)
                    if isinstance(messages, list)
                    else 0
                )

                started = time.perf_counter()
                reply, tokens_used = await func(*args, **kwargs)
                latency_ms = (time.perf_counter() - started) * 1000

                try:
                    loop = asyncio.get_running_loop()
                    future = loop.run_in_executor(
                        None,
                        _log_to_mlflow,
                        model_name,
                        context,
                        prompt_length,
                        latency_ms,
                        reply,
                        tokens_used,
                    )
                    # Consume any exception to avoid unhandled-future warnings;
                    # MLflow logging is best-effort and non-critical.
                    future.add_done_callback(
                        lambda f: f.exception() if not f.cancelled() else None
                    )
                except Exception:
                    pass

                return reply, tokens_used

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> tuple[str, int]:
            context = get_tracking_context()
            messages = args[0] if args else kwargs.get("messages", [])
            prompt_length = (
                sum(len(m.get("content", "")) for m in messages)
                if isinstance(messages, list)
                else 0
            )

            started = time.perf_counter()
            reply, tokens_used = func(*args, **kwargs)
            latency_ms = (time.perf_counter() - started) * 1000

            _log_to_mlflow(
                model_name, context, prompt_length, latency_ms, reply, tokens_used
            )

            return reply, tokens_used

        return wrapper

    return decorator
