from functools import lru_cache

from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    claude_api_key: str = ""
    gemini_api_key: str = ""

    openai_model: str = "gpt-4o-mini"
    claude_model: str = "claude-3-sonnet-20240229"
    gemini_model: str = "gemini-pro"

    temperature: float = 0.3
    max_tokens: int = 1024

    system_prompt: str = (
        "You are a CSS exam preparation assistant for Pakistan's CSS competitive exam. "
        "Answer questions about Pakistan affairs, history, current affairs, essay topics, "
        "and general knowledge."
    )

    allowed_origins: str = "http://localhost:5173,https://cssprep.ai"
    rate_limit: str = "30/minute"

    database_url: str = "sqlite+aiosqlite:///./css_prep_ai.db"
    mlflow_tracking_uri: str = "http://localhost:5001"
    mlflow_experiment_name: str = "css-prep-ai-llm"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def limiter(self) -> Limiter:
        return Limiter(key_func=get_remote_address)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
