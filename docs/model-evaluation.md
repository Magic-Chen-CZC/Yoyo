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
- SQL grounding quality
- Live-info uncertainty handling
- Profile-aware guide generation quality
- Hallucination rate on tourism questions
- Cost
- Latency
- Context handling
- Multi-turn dialogue continuity

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
5. planner handoff / route-edit extraction
6. profile-aware guide generation quality
7. multilingual QA samples

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
- SQL grounding-aware evaluation dimensions
- planner handoff extraction evaluation dimensions
- profile-aware guide generation evaluation dimensions
- per-result score output
- summary average score per model
- batch multi-model evaluation via `evals/models.yaml`

## Current reporting direction
- overall ranking
- category breakdown
- language breakdown
- provider/model comparison in markdown output

## Next improvements
- further strengthen rubrics beyond rule-based heuristics
- expand tourism-specific multilingual datasets
- deepen route-edit and planner extraction coverage
- add richer report exports if needed

## Engineering requirement
Keep provider/model selection configurable through env and a model abstraction layer. Do not bind business logic directly to one SDK.
