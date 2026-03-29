import asyncio
from collections.abc import AsyncIterator

from app.config import settings
from app.mlops.mlflow_tracker import track_llm_call


def _model(system_prompt: str):
    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel(
        model_name=settings.gemini_model, system_instruction=system_prompt
    )


def _to_gemini_parts(messages: list[dict[str, str]]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        gemini_role = "model" if role == "assistant" else "user"
        if role == "system":
            continue
        result.append({"role": gemini_role, "parts": [content]})
    return result


@track_llm_call(model_name="gemini-1.5-flash")
async def call_gemini(
    messages: list[dict[str, str]], system_prompt: str | None = None
) -> tuple[str, int]:
    prompt = system_prompt or settings.system_prompt
    parts = _to_gemini_parts(messages)
    generation_config = {
        "temperature": settings.temperature,
        "max_output_tokens": settings.max_tokens,
    }

    response = await asyncio.to_thread(
        _model(prompt).generate_content,
        parts,
        generation_config=generation_config,
    )

    reply = response.text or ""
    usage = getattr(response, "usage_metadata", None)
    tokens = getattr(usage, "total_token_count", 0) if usage else 0
    return reply, int(tokens or 0)


async def stream_gemini(
    messages: list[dict[str, str]], system_prompt: str | None = None
) -> AsyncIterator[str]:
    prompt = system_prompt or settings.system_prompt
    parts = _to_gemini_parts(messages)
    generation_config = {
        "temperature": settings.temperature,
        "max_output_tokens": settings.max_tokens,
    }

    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    def _sync_stream() -> None:
        try:
            for chunk in _model(prompt).generate_content(
                parts,
                generation_config=generation_config,
                stream=True,
            ):
                text = getattr(chunk, "text", "")
                if text:
                    loop.call_soon_threadsafe(queue.put_nowait, text)
        except Exception:
            pass
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    loop.run_in_executor(None, _sync_stream)

    while True:
        item = await queue.get()
        if item is None:
            break
        yield item
