"""Shared pydantic input models: strict lengths and formats, no free-form
fields without limits."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ChatMessageIn(BaseModel):
    conversation_id: str | None = Field(default=None, max_length=64)
    text: str = Field(min_length=1, max_length=2000)
    locale: str = Field(default="fr", pattern="^(fr|ar)$")

    @field_validator("text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("text must not be empty")
        return value


class AgentTokenIn(BaseModel):
    agent: str = Field(min_length=2, max_length=64, pattern="^[A-Z0-9_]+$")
    tool: str = Field(min_length=2, max_length=64, pattern="^[A-Z0-9_]+$")
    operation: str = Field(default="execute", pattern="^[a-z_]+$")
    data_scope: str = Field(default="OWN", pattern="^[A-Z_]+$")


class VectorRetrievalIn(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    language: str = Field(default="fr", pattern="^(fr|ar)$")
    top_k: int = Field(default=5, ge=1, le=20)


class GraphRetrievalIn(BaseModel):
    template: str = Field(min_length=2, max_length=64, pattern="^[a-z_]+$")
    params: dict[str, str] = Field(default_factory=dict)


class DocumentIndexIn(BaseModel):
    document_id: str = Field(min_length=1, max_length=64)


class HumanHandoffIn(BaseModel):
    conversation_id: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=3, max_length=500)


class PublicChatIn(BaseModel):
    text: str = Field(min_length=2, max_length=1000)
    language: str = Field(default='fr', pattern='^(fr|ar)$')


class SecurityGateIn(BaseModel):
    text: str = Field(default="", max_length=2000)
    request_type: str = Field(pattern="^(chat|tool|upload)$")
    source_user_id: str | None = Field(default=None, max_length=64)
    agent: str | None = Field(default=None, max_length=64)
    tool: str | None = Field(default=None, max_length=64)
    filename: str | None = Field(default=None, max_length=255)
