# Evaluation Fields

This file documents the fields recorded by the current evaluation framework and the current OpenRouter probing status.

## Per-query result fields (`EvalResult`)
- `query_id`: stable query identifier from the dataset
- `provider`: model provider used for the run
- `model`: exact model id used for the run
- `prompt`: full query text sent to the model
- `response_text`: raw model output text
- `latency_ms`: elapsed time for this single request in milliseconds
- `prompt_tokens`: prompt token count if returned by the provider
- `completion_tokens`: completion token count if returned by the provider
- `total_tokens`: total token count if returned by the provider
- `estimated_input_cost`: estimated input-side cost from local pricing metadata
- `estimated_output_cost`: estimated output-side cost from local pricing metadata
- `total_cost`: provider-reported cost when available, otherwise estimated input+output cost
- `parameter_size`: parameter-size metadata if public, otherwise `not_public` or `null`
- `metadata`: additional query metadata, currently including:
  - `category`
  - `language`
  - `poi_name` or `phrase` when present in the dataset

## Per-query score fields (`EvalScore`)
- `query_id`
- `provider`
- `model`
- `category`
- `score`
- `max_score`
- `rationale`

## Per-model summary fields (`EvalSummary`)
- `provider`
- `model`
- `total_queries`
- `avg_latency_ms`
- `estimated_total_input_cost`
- `estimated_total_output_cost`
- `estimated_total_cost`
- `avg_prompt_tokens`
- `avg_completion_tokens`
- `avg_total_tokens`
- `avg_score`

## Output artifacts
For each model run, the framework can emit:
- `*_results.json`
- `*_scores.json`
- `evals/results/benchmark_results.xlsx`

For E2E QA benchmark exports, the workbook should also include:
- `e2e_cases` sheet for case-level rows
- `e2e_summary` sheet for per-model rollups

## E2E QA benchmark additional fields
The current eval framework fields above describe model-only benchmark output.
For true `/api/v1/qa/ask` end-to-end QA benchmark runs, we additionally need two levels of fields:

### Run-level fields
- `run_id`
- `round_id`
- `round_name`
- `benchmark_type`
- `dataset_name`
- `dataset_version`
- `total_cases`
- `environment_name`
- `base_url`
- `api_revision`
- `worker_revision`
- `rag_enabled`
- `tts_enabled`
- `live_info_enabled`
- `provider`
- `model`
- `start_time`
- `end_time`
- `avg_latency_ms`
- `p95_latency_ms`
- `estimated_total_cost`
- `avg_score`
- `completion_rate`
- `qualified_category_count`
- `overall_qualified`
- `blocking_assessment`
- `key_findings`
- `notes`
- `log_doc_path`
- `feishu_doc_url`

### Case-level fields
- `run_id`
- `case_id`
- `query_id`
- `category`
- `language`
- `title`
- `mode`
- `operation`
- `query_zh`
- `expected_intent`
- `expected_data_source`
- `session_required`
- `profile_id`
- `fixture_mode`
- `variant_group`
- `session_state`
- `provider`
- `model`
- `request_text`
- `response_text`
- `http_status`
- `api_status`
- `latency_ms`
- `prompt_tokens`
- `completion_tokens`
- `total_tokens`
- `estimated_total_cost`
- `score`
- `max_score`
- `decision`
- `confidence`
- `degraded`
- `degraded_reason`
- `retrieval_strategy`
- `rag_backend_ready`
- `rag_query_status`
- `supported`
- `artifact_path`
- `notes`

### Case definition helper fields
These fields live in the dataset and should be carried into run-level inspection or manual review when useful:
- `data_anchor`
- `assertions`
- `models`
- `data_sources`

## Translation benchmark fields

### Translation per-case fields
- `run_id`
- `run_started_at`
- `suite`
- `dataset_name`
- `dataset_version`
- `case_id`
- `question_type`
- `category`
- `direction`
- `source_language`
- `target_language`
- `user_language`
- `provider`
- `model`
- `query`
- `response_text`
- `status`
- `reason`
- `execution_path`
- `latency_ms`
- `prompt_tokens`
- `completion_tokens`
- `total_tokens`
- `estimated_input_cost`
- `estimated_output_cost`
- `estimated_total_cost`
- `llm_error`
- `raw_text`
- `structured_output_valid`
- `attempt_count`
- `retry_performed`
- `attempts`
- `mode`
- `user_visible_lines`
- `display_blocks`
- `downstream_intent` (routing suite only)
- `downstream_confidence` (routing suite only)
- `score`
- `max_score`
- `passed_checks`
- `failed_checks`
- `score_detail`
- `case_metadata`

### Translation summary fields
- `run_id`
- `suite`
- `dataset_name`
- `dataset_version`
- `provider`
- `model`
- `total_cases`
- `avg_latency_ms`
- `avg_score`
- `degraded_cases`
- `sum_prompt_tokens`
- `sum_completion_tokens`
- `sum_total_tokens`
- `estimated_total_cost`
- `execution_paths`
- `category_breakdown`
- `by_language`
- `by_direction`
- `by_question_type`

### Translation workbook sheets
- `translation_cases` for per-case rows
- `translation_model_compare` for per-run, per-language, per-question-type comparison rows

### Translation dataset rules
- Every translation benchmark case must declare explicit language fields.
- `product_translation` cases must include: `id`, `query`, `question_type`, `category`, `direction`, `user_language`, `source_language`, `target_language`.
- `routing_preprocess` cases must include: `id`, `query`, `question_type`, `category`, `direction`, `user_language`, `source_language`, `target_language`, `expected_intent`.
- `direction` must match `source_language` and `target_language`; display cases use the `_display` suffix.
- Extreme multilingual cases are not allowed in the strict translation benchmark datasets. Keep wrapper-style explicit translation, bilingual display, and light entity mixing, but do not include queries that stack three or more natural-language layers in a single source utterance.
- The runner no longer fills in missing language fields with fallback defaults; invalid cases fail fast before execution.
- Plain MT benchmark rows now persist upstream failure and retry observability, including `llm_error`, `raw_text`, and per-attempt `attempts` snapshots.
- Plain MT now uses sequential retry semantics by default: each attempt is capped by `translator_plain_mt_attempt_timeout_seconds` (currently `1.0s`), and retry is only performed for retryable upstream errors up to `translator_plain_mt_max_attempts` (currently `2`).

## Current OpenRouter probe status
The following model ids were probed through OpenRouter with the latest key:
- `openai/gpt-5.4-mini`
- `openai/gpt-5.4`
- `google/gemini-3.1-pro-preview`
- `google/gemini-3-flash-preview`
- `anthropic/claude-sonnet-4.6`

Current result:
- all five now return successful responses

Observed minimal probe samples:
- `openai/gpt-5.4-mini` → prompt_tokens=11, completion_tokens=5, total_tokens=16, cost=0.00003075
- `openai/gpt-5.4` → prompt_tokens=11, completion_tokens=5, total_tokens=16, cost=0.0001025
- `google/gemini-3.1-pro-preview` → prompt_tokens=5, completion_tokens=108, total_tokens=113, cost=0.001306
- `google/gemini-3-flash-preview` → prompt_tokens=5, completion_tokens=1, total_tokens=6, cost=0.0000055
- `anthropic/claude-sonnet-4.6` → prompt_tokens=13, completion_tokens=4, total_tokens=17, cost=0.000099

## Current recommendation before full benchmark
1. Keep the result fields listed above as the official benchmark output schema.
2. Use the current OpenRouter model matrix as the first benchmark shortlist.
3. Run the 81-query English benchmark next, then generate cost/latency/score comparison.
