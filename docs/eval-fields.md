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
