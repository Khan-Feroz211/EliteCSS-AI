from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from typing import Literal


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    messages: list[Message]
    model: Literal["gpt", "claude", "gemini"] = "gpt"

    model_config = {
        "json_schema_extra": {
            "example": {
                "messages": [{"role": "user", "content": "What is CSS exam?"}],
                "model": "gpt",
            }
        }
    }

    @property
    def last_message(self) -> str:
        return self.messages[-1].content if self.messages else ""

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, value: list[Message]) -> list[Message]:
        if not value:
            raise ValueError("messages must contain at least one message")
        return value


class ChatResponse(BaseModel):
    reply: str
    model: str
    tokens_used: int
    latency_ms: float


class HealthResponse(BaseModel):
    status: str
    uptime: float
    models_available: list[str]


class FeedbackRequest(BaseModel):
    message_id: str = Field(..., min_length=1, max_length=64)
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field(default="", max_length=1000)


class FeedbackResponse(BaseModel):
    status: str
    feedback_id: int
    linked_to_run: bool


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)


class UserOut(BaseModel):
    id: int
    email: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int
    email: str


class ModelChoice(str, Enum):
    gpt = "gpt"
    claude = "claude"
    gemini = "gemini"


class StreamRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    model: ModelChoice = ModelChoice.gpt
    history: list[Message] = Field(default_factory=list)
