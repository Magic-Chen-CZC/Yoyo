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
7. `docs/model-evaluation.md`

Before broad QA verification, finish the shared overlap contracts listed in `docs/contracts.md` and the Shared / coordination section of `docs/todo.md`.
Then inspect the current code and continue the next unchecked item in `docs/todo.md`.

## Model strategy
- Initial default model target for product experiments: Claude Sonnet 4.6
- Keep model provider/model name configurable via env
- We will later evaluate Qwen, Gemini, and others across English and multilingual tourism tasks
- Do not hardcode business logic to any specific model SDK yet

## Current continuation point
- Shared overlap contracts are already stabilized in `docs/contracts.md`
- Continue from `docs/todo.md`, primarily along the **B track** unless the user says otherwise
- First-round benchmark artifacts are in `evals/results/`
- Excel export is at project root: `benchmark_results.xlsx`
- Latest benchmark comparison report has been written to Feishu separately
