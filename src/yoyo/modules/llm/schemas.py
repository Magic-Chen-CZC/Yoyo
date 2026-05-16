from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PromptMessage(BaseModel):
    role: str
    content: str


class GenerationOptions(BaseModel):
    max_tokens: int = 700
    temperature: float = 0.2
    timeout_seconds: float = 45.0


class LLMRequest(BaseModel):
    provider: str
    model: str
    messages: list[PromptMessage] = Field(default_factory=list)
    options: GenerationOptions = Field(default_factory=GenerationOptions)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMUsage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost: float | None = None


class LLMError(BaseModel):
    error_type: str
    message: str
    retryable: bool = False
    status_code: int | None = None
    provider_error_code: str | None = None


class LLMResponse(BaseModel):
    text: str
    provider: str
    model: str
    usage: LLMUsage = Field(default_factory=LLMUsage)
    finish_reason: str | None = None
    latency_ms: float = 0.0
    raw_response: dict[str, Any] = Field(default_factory=dict)
    error: LLMError | None = None
