# Yoyo

Backend-first FastAPI project for the Yoyo Beijing tour intelligent guide system.

## Current scope
- Modular monolith backend
- Planner module
- Controlled single-agent Guide QA module
- PostgreSQL + Redis
- Versioned itineraries and async guide generation jobs
- Current B-side implementation is SQL-first for attraction/profile knowledge
- Live search is currently reserved for real-time travel changes
- RAG is deferred for now and remains a future evolution path if SQL-backed knowledge becomes insufficient

## Local setup
1. Install Python 3.12 and `uv`
2. Copy `.env.example` to `.env`
3. Start infra:
   - `docker compose up -d`
4. Create a project virtualenv and install dependencies:
   - `python3 -m venv .venv`
   - `.venv/bin/python -m pip install -e ".[dev]"`
5. Run migrations:
   - `.venv/bin/alembic upgrade head`
6. Seed mock SQL-first knowledge data into PostgreSQL:
   - `PYTHONPATH=src .venv/bin/python src/yoyo/scripts/seed_mock_knowledge.py`
7. Start app:
   - `.venv/bin/uvicorn yoyo.app:app --reload`

Note:
- Config now loads `.env` from the project root, so scripts can still read keys correctly even when launched from outside the repo directory as long as `PYTHONPATH=src` is set.

## Development notes
- API prefix: `/api/v1`
- Source code lives in `src/yoyo`
- Tests live in `tests`
- Project continuity notes live in `CLAUDE.md`
- Architecture notes live in `docs/architecture.md`
- Working todo lives in `docs/todo.md`
- Collaboration split lives in `docs/collaboration.md`
- Shared overlap contracts live in `docs/contracts.md`
- Previous todo snapshot lives in `docs/todo-archive-v1.md`
- Model evaluation plan lives in `docs/model-evaluation.md`
- Teammate setup guide lives in `docs/dev-setup-for-teammates.md`
- Current B-side implementation overview lives in `docs/b-stack-implementation-overview.md`
- Future real-data preparation checklist lives in `docs/b-stack-preparation-checklist.md`
- A-track branch summary lives in `docs/a-track-branch-notes.md`
- A-track module explainer lives in `docs/a-track-modules-explained.md`

## Current team workflow
- A and B should first finish the shared overlap contracts in `docs/contracts.md`
- Use the Shared / coordination checklist in `docs/todo.md` as the gate before broader QA verification
- Only after those shared contracts are stable should we run broader QA validation and parallel feature work without contract churn

## Current SQL-first run flow
If you want to run the current B-side implementation locally, the intended order is:
1. Start PostgreSQL and Redis with Docker Compose
2. Apply Alembic migrations
3. Seed the mock attraction/profile data into PostgreSQL
4. Start the FastAPI app

At this phase:
- attraction basics and attraction introduction come from PostgreSQL-backed data
- user profiles come from PostgreSQL-backed data
- live search is only for same-day dynamic facts
- RAG is not part of the current runtime path
- a shared runtime LLM layer now exists for product QA and Guide generation text generation

## Runtime LLM generation notes
- Shared runtime provider wiring now lives under `src/yoyo/modules/llm/`.
- This layer is intended for product QA and Guide generation runtime calls, not only evaluation scripts.
- Current first-step implementation supports Anthropic, OpenRouter, and Gemini-style runtime providers.
- Product code should use the runtime layer instead of calling eval providers directly.
- Guide generation now attempts runtime LLM generation for guide text fields and falls back to the deterministic builder if the LLM call fails.
- QA now attempts runtime LLM generation for attraction explanation, trip assistant, translation, and live-info wording, while keeping rules-first routing and fallback output.

## Evaluation harness
- The current eval phase is aligned to the SQL-first architecture and now includes planner handoff, multilingual samples, and guide-generation-oriented quality prompts.
- Generate and run batch model evals with:
  - `.venv/bin/python evals/run_eval.py --provider anthropic --model claude-sonnet-4-6 --dataset evals/datasets/english_queries_81.json`
  - `.venv/bin/python evals/run_eval.py --provider google --model gemini-2.5-pro --dataset evals/datasets/english_queries_81.json`
  - `.venv/bin/python evals/run_eval.py --provider dashscope --model qwen-max --dataset evals/datasets/english_queries_81.json`
  - `.venv/bin/python evals/run_batch_eval.py --dataset evals/datasets/english_queries_81.json`
- Results and scores are written to `evals/results/`
- While a batch is running, progress is written incrementally to:
  - `evals/results/batch_progress.json`
  - `evals/results/*_progress.json`
- Partial per-model `results` / `scores` files are also flushed during execution, so interrupted runs can still be inspected.
