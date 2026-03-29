from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.config import settings
from app.mlops.mlflow_tracker import track_llm_call


def _client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=settings.openai_api_key)


def _prepare_messages(
    messages: list[dict[str, str]], system_prompt: str
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": system_prompt},
        *messages,
    ]


@track_llm_call(model_name="gpt-4o-mini")
async def call_gpt(
    messages: list[dict[str, str]], system_prompt: str | None = None
) -> tuple[str, int]:
    prompt = system_prompt or settings.system_prompt
    response = await _client().chat.completions.create(
        model=settings.openai_model,
        messages=_prepare_messages(messages, prompt),
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
    )

    reply = response.choices[0].message.content or ""
    tokens = response.usage.total_tokens if response.usage else 0
    return reply, tokens


async def stream_gpt(
    messages: list[dict[str, str]], system_prompt: str | None = None
) -> AsyncIterator[str]:
    prompt = system_prompt or settings.system_prompt
    stream = await _client().chat.completions.create(
        model=settings.openai_model,
        messages=_prepare_messages(messages, prompt),
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta
