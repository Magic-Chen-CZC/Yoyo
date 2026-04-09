from typing import Any

from pydantic import BaseModel, Field


class EvalQuery(BaseModel):
    id: str
    category: str
    language: str
    prompt: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvalResult(BaseModel):
    query_id: str
    provider: str
    model: str
    prompt: str
    response_text: str
    latency_ms: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    estimated_input_cost: float | None = None
    estimated_output_cost: float | None = None
    total_cost: float | None = None
    parameter_size: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvalScore(BaseModel):
    query_id: str
    provider: str
    model: str
    category: str
    score: float
    max_score: float
    rationale: str


class EvalSummary(BaseModel):
    provider: str
    model: str
    total_queries: int
    avg_latency_ms: float
    estimated_total_input_cost: float
    estimated_total_output_cost: float
    estimated_total_cost: float = 0.0
    avg_prompt_tokens: float = 0.0
    avg_completion_tokens: float = 0.0
    avg_total_tokens: float = 0.0
    avg_score: float = 0.0
