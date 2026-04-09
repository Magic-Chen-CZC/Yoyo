# Model Evaluation Notes

## Current recommendation
Default initial product experiments should start with **Claude Sonnet 4.6** because it is a good balance of quality, multilingual ability, and latency for the Yoyo backend.

## Why not lock in one model yet
We should compare multiple providers and models on Yoyo-specific tasks before finalizing production usage.

## Candidate models to evaluate later
- Claude Sonnet 4.6
- Claude Haiku 4.5
- Gemini family
- Qwen family
- other multilingual-capable models if needed

## Evaluation dimensions
- English tour-guide answer quality
- Non-English / multilingual answer quality
- Structured extraction reliability
- Intent classification quality
- Route-edit instruction understanding
- Hallucination rate on tourism questions
- Cost
- Latency
- Context handling

## Language-region guidance to test
### English-first markets
Good starting candidates:
- Claude Sonnet 4.6
- Gemini 2.5 Pro / Flash (to be benchmarked)

### Multilingual / mixed-language markets
Good starting candidates:
- Claude Sonnet 4.6
- Qwen multilingual-capable models
- Gemini multilingual-capable models

## Benchmark design implemented in repo
We now have a first evaluation harness with:
- template-based batch query generation
- provider adapters for Anthropic / Gemini / Qwen-compatible APIs
- result persistence to JSON
- summary metrics for latency and estimated cost

Current dataset covers:
1. attraction explanation
2. translation
3. live info
4. trip assistant

For each model capture:
- model name
- provider
- parameter size if public
- estimated input/output cost
- average latency
- response text
- category/language metadata

## Current commands
- `.venv/bin/python evals/run_eval.py --provider anthropic --model claude-sonnet-4-6`
- `.venv/bin/python evals/run_eval.py --provider google --model gemini-2.5-pro`
- `.venv/bin/python evals/run_eval.py --provider dashscope --model qwen-max`

## Current scoring support
We now have:
- rubric-based automatic scoring
- per-result score output
- summary average score per model
- batch multi-model evaluation via `evals/models.yaml`

## Next improvements
- strengthen rubrics beyond keyword heuristics
- add more tourism-specific multilingual datasets
- add route-edit and planner extraction scenarios
- add CSV/markdown report output
- add side-by-side comparative report generation

## Engineering requirement
Keep provider/model selection configurable through env and a model abstraction layer. Do not bind business logic directly to one SDK.
