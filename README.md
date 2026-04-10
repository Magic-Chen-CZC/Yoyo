# Yoyo

Backend-first FastAPI project for the Yoyo Beijing tour intelligent guide system.

## Current scope
- Modular monolith backend
- Planner module
- Controlled single-agent Guide QA module
- PostgreSQL + Redis
- Versioned itineraries and async guide generation jobs

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
6. Start app:
   - `.venv/bin/uvicorn yoyo.app:app --reload`

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
- A-track branch summary lives in `docs/a-track-branch-notes.md`
- A-track module explainer lives in `docs/a-track-modules-explained.md`

## Current team workflow
- A and B should first finish the shared overlap contracts in `docs/contracts.md`
- Use the Shared / coordination checklist in `docs/todo.md` as the gate before broader QA verification
- Only after those shared contracts are stable should we run broader QA validation and parallel feature work without contract churn

## Evaluation harness
- Generate and run batch model evals with:
  - `.venv/bin/python evals/run_eval.py --provider anthropic --model claude-sonnet-4-6 --dataset evals/datasets/english_queries_81.json`
  - `.venv/bin/python evals/run_eval.py --provider google --model gemini-2.5-pro --dataset evals/datasets/english_queries_81.json`
  - `.venv/bin/python evals/run_eval.py --provider dashscope --model qwen-max --dataset evals/datasets/english_queries_81.json`
  - `.venv/bin/python evals/run_batch_eval.py --dataset evals/datasets/english_queries_81.json`
- Results and scores are written to `evals/results/`
