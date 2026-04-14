# schemas.py 定义 Eval 模块的核心数据结构。
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


class HardCheckResult(BaseModel):
    query_id: str
    provider: str
    model: str
    category: str
    passed: bool
    score_cap: float | None = None
    failed_checks: list[str] = Field(default_factory=list)


class JudgeResult(BaseModel):
    query_id: str
    provider: str
    model: str
    category: str
    judge_provider: str
    judge_model: str
    judge_version: str
    rubric_version: str
    overall_score: float
    max_score: float
    decision: str
    confidence: float
    dimension_scores: dict[str, float] = Field(default_factory=dict)
    dimension_rationales: dict[str, str] = Field(default_factory=dict)
    issues: list[dict[str, Any]] = Field(default_factory=list)
    hard_constraint_summary: dict[str, Any] = Field(default_factory=dict)
    judge_latency_ms: float = 0.0
    judge_prompt_tokens: int | None = None
    judge_completion_tokens: int | None = None
    judge_total_tokens: int | None = None
    judge_total_cost: float | None = None
    raw_judge_text: str = ""


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
