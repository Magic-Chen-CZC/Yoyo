from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


TranslationExecutionPath = Literal[
    "llm_structured",
    "plain_mt",
    "formatter_fallback",
    "disabled",
    "provider_error",
    "timeout",
    "invalid_output",
    "fail_open",
]


class TranslationDisplayBlock(BaseModel):
    role: Literal["instruction", "translation", "original"]
    language: str
    text: str


class RoutingTranslationStructuredOutput(BaseModel):
    text: str
    status: Literal["ok", "degraded"]
    reason: str | None = None
    source_language: str | None = None
    target_language: str


class AnswerTranslationStructuredOutput(BaseModel):
    text: str
    status: Literal["ok", "degraded"]
    reason: str | None = None
    source_language: str
    target_language: str


class QATranslationStructuredOutput(BaseModel):
    answer: str
    status: Literal["ok", "degraded", "clarification"]
    reason: str | None = None
    mode: Literal["direct_translation", "bilingual_for_display", "clarification", "degraded"]
    source_language: str | None = None
    target_language: str | None = None
    translated_text: str | None = None
    user_instruction: str | None = None
    user_visible_lines: list[str] = Field(default_factory=list)


class TranslatorResult(BaseModel):
    text: str
    status: Literal["ok", "degraded", "clarification"]
    reason: str | None = None
    source_language: str | None = None
    target_language: str | None = None
    mode: str
    degraded: bool = False
    execution_path: TranslationExecutionPath
    provider: str | None = None
    model: str | None = None
    latency_ms: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    estimated_input_cost: float | None = None
    estimated_output_cost: float | None = None
    estimated_total_cost: float | None = None
    display_blocks: list[TranslationDisplayBlock] = Field(default_factory=list)
    user_visible_lines: list[str] = Field(default_factory=list)
    llm_error: dict[str, object] | None = None
    structured_output_valid: bool | None = None
    raw_text: str | None = None
    attempt_count: int = 1
    retry_performed: bool = False
    attempts: list[dict[str, object]] = Field(default_factory=list)
