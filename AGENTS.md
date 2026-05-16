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
1. `AGENTS.md`
2. `README.md`
3. `docs/todo-phase-2.md`
4. `docs/phase-2-summary.md`
5. `docs/dev-retrospective.md`

README must remain the main document index for current architectural and implementation work. Whenever architecture, framework, routing strategy, evaluation direction, testing strategy, or phase-entry structure changes, update the relevant docs and add or refresh the README entry in the same pass so future sessions can resume from the current phase documents.
Also keep `docs/current-session-summary.md` as a historical session log when needed, but use `docs/phase-2-summary.md` as the active continuation summary for the current phase.
After each meaningful development or debugging pass, also append a short issue record to `docs/dev-retrospective.md` using the format: problem / cause / improvement.

The repository is now past the earlier split-phase build stage and is in the next-phase documentation, testing, and QA-hardening cycle.
A track is already complete on the integration branch.
When continuing, inspect the current code and continue the next unchecked item in `docs/todo-phase-2.md`, using `docs/phase-2-summary.md` as the current continuation summary and `docs/feature-test-guide.md` as the feature-level testing overview.

## Model strategy
- Initial default model target for product experiments: Codex Sonnet 4.6
- Keep model provider/model name configurable via env
- We will later evaluate Qwen, Gemini, and others across English and multilingual tourism tasks
- Do not hardcode business logic to any specific model SDK yet

## Current continuation point
- Shared overlap contracts are already stabilized in `docs/contracts.md`
- A track has been merged and completed on the integration branch
- Continue from `docs/todo-phase-2.md`, focusing on documentation entrypoint reset, feature-level testing documentation, and QA-hardening preparation
- Use `docs/phase-2-summary.md` as the active continuation summary
- Use `docs/feature-test-guide.md` as the feature-by-feature testing overview
- Round 1 benchmark artifacts are available in `evals/results_round1_real/`
- Gemini round 2 artifacts are available in `evals/results_gemini_round2_200/`
- Excel exports exist at project root, including `benchmark_results_round1_real.xlsx` and `benchmark_results_gemini_round2_200.xlsx`
- Local summary docs exist for model selection and Gemini deep evaluation; Feishu sync may still need fresh MCP user authorization
