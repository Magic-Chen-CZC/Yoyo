# Yoyo project instructions

## Goal
Build the backend for the Yoyo Beijing-tour intelligent guide product.

## Architecture decisions
- Backend-first
- FastAPI + Python 3.12
- Modular monolith first
- Planner = workflow/state machine/rules + limited LLM
- Guide QA = controlled single-agent with domain guard, intent router, skill whitelist, validators
- PostgreSQL + Redis
- Async jobs for guide generation
- Core concepts: itinerary_version, guide_generation_job, asset_status

## Current implementation strategy
1. Bootstrap backend scaffold
2. Add infra/config/db/redis/alembic
3. Create initial core models
4. Implement first vertical slice:
   - questionnaire submission
   - itinerary creation
   - itinerary_version creation
   - guide_generation_job enqueue + query
5. Add tests before expanding to QA/map/GPS

## How to continue in a new session
When starting a new session, read in this order:
1. `CLAUDE.md`
2. `README.md`
3. `docs/architecture.md`
4. `docs/contracts.md`
5. `docs/collaboration.md`
6. `docs/todo.md`
7. `docs/b-stack-implementation-overview.md`
8. `docs/model-evaluation.md`
9. `docs/round1-model-selection-summary.md`
10. `docs/gemini-round2-summary.md`

The repository is now on an integrated A+B path rather than the earlier split-phase plan.
A track is already complete on the integration branch.
When continuing, inspect the current code and continue the next unchecked item in `docs/todo.md`, focusing on B-side follow-up work such as real data integration, evaluation hardening, prompt optimization, and final test coverage.

## Model strategy
- Initial default model target for product experiments: Claude Sonnet 4.6
- Keep model provider/model name configurable via env
- We will later evaluate Qwen, Gemini, and others across English and multilingual tourism tasks
- Do not hardcode business logic to any specific model SDK yet

## Current continuation point
- Shared overlap contracts are already stabilized in `docs/contracts.md`
- A track has been merged and completed on the integration branch
- Continue from `docs/todo.md`, focusing on the remaining unchecked B-side follow-up items
- Round 1 benchmark artifacts are available in `evals/results_round1_real/`
- Gemini round 2 artifacts are available in `evals/results_gemini_round2_200/`
- Excel exports exist at project root, including `benchmark_results_round1_real.xlsx` and `benchmark_results_gemini_round2_200.xlsx`
- Local summary docs exist for model selection and Gemini deep evaluation; Feishu sync may still need fresh MCP user authorization
