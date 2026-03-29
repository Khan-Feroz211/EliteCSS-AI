from collections.abc import AsyncIterator

from anthropic import AsyncAnthropic

from app.config import settings
from app.mlops.mlflow_tracker import track_llm_call


def _client() -> AsyncAnthropic:
    return AsyncAnthropic(api_key=settings.claude_api_key)


def _split_messages(
    messages: list[dict[str, str]], system_prompt: str
) -> tuple[str, list[dict[str, str]]]:
    active_system_prompt = system_prompt
    prepared: list[dict[str, str]] = []

    for item in messages:
        role = item.get("role", "user")
        if role == "system":
            active_system_prompt = (
                f"{active_system_prompt}\n{item.get('content', '')}".strip()
            )
            continue
        if role == "assistant":
            prepared.append({"role": "assistant", "content": item.get("content", "")})
            continue
        prepared.append({"role": "user", "content": item.get("content", "")})

    return active_system_prompt, prepared


@track_llm_call(model_name="claude-sonnet-4-6")
async def call_claude(
    messages: list[dict[str, str]], system_prompt: str | None = None
) -> tuple[str, int]:
    prompt = system_prompt or settings.system_prompt
    active_system_prompt, prepared_messages = _split_messages(messages, prompt)
    response = await _client().messages.create(
        model=settings.claude_model,
        system=active_system_prompt,
        max_tokens=settings.max_tokens,
        temperature=settings.temperature,
        messages=prepared_messages,
    )

    text_blocks = [block.text for block in response.content if hasattr(block, "text")]
    reply = "".join(text_blocks)
    usage = response.usage
    tokens = int((usage.input_tokens or 0) + (usage.output_tokens or 0)) if usage else 0
    return reply, tokens


async def stream_claude(
    messages: list[dict[str, str]], system_prompt: str | None = None
) -> AsyncIterator[str]:
    prompt = system_prompt or settings.system_prompt
    active_system_prompt, prepared_messages = _split_messages(messages, prompt)

    async with _client().messages.stream(
        model=settings.claude_model,
        system=active_system_prompt,
        max_tokens=settings.max_tokens,
        temperature=settings.temperature,
        messages=prepared_messages,
    ) as stream:
        async for text in stream.text_stream:
            if text:
                yield text
