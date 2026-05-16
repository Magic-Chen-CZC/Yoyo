# Yoyo

Backend-first FastAPI project for the Yoyo Beijing-tour intelligent guide product.

The current phase is documentation, testing, and QA-hardening. The backend already has the core product slices in place: onboarding, itinerary planning, session/GPS/playback state, guide generation, QA, SQL-first knowledge retrieval, RAG fallback scaffolding, navigation text routing, translation preprocessing, and benchmark tooling.

## Quick Start

1. Install Python 3.12 and `uv`.
2. Copy `.env.example` to `.env`.
3. Start local infra:
   ```bash
   docker compose up -d
   ```
4. Create a virtualenv and install dependencies:
   ```bash
   python3 -m venv .venv
   .venv/bin/python -m pip install -e ".[dev]"
   ```
5. Run migrations:
   ```bash
   .venv/bin/alembic upgrade head
   ```
6. Seed mock SQL-first knowledge data:
   ```bash
   PYTHONPATH=src .venv/bin/python src/yoyo/scripts/seed_mock_knowledge.py
   ```
7. Start the app:
   ```bash
   .venv/bin/uvicorn yoyo.app:app --reload
   ```

Config loads `.env` from the project root. When running scripts from outside the repo directory, keep `PYTHONPATH=src`.

## Development Notes

- API prefix: `/api/v1`
- Source code: `src/yoyo`
- Tests: `tests`
- Main runtime model/provider selection is configurable through env and the shared LLM runtime under `src/yoyo/modules/llm/`.
- Current formal QA hard benchmark chain uses the main `/api/v1/qa/ask` path with `dashscope/qwen-turbo` unless a run explicitly overrides the model.

## Documentation

Start from [docs/README.md](docs/README.md). It is now the detailed document map.

High-value entry points:

- Current phase: [docs/phase-2-summary.md](docs/phase-2-summary.md)
- Active todo: [docs/todo-phase-2.md](docs/todo-phase-2.md)
- Architecture: [docs/architecture.md](docs/architecture.md)
- Shared contracts: [docs/contracts.md](docs/contracts.md)
- QA index: [docs/qa/README.md](docs/qa/README.md)
- QA routing: [docs/qa/routing/README.md](docs/qa/routing/README.md)
- QA intent rules: [docs/qa/intent-rules/README.md](docs/qa/intent-rules/README.md)
- Navigation QA: [docs/qa/navigation/README.md](docs/qa/navigation/README.md)
- Testing index: [docs/testing/README.md](docs/testing/README.md)
- Evaluation index: [docs/evals/README.md](docs/evals/README.md)
- Frontend/API docs: [docs/frontend/README.md](docs/frontend/README.md)

For a new AI session, read in this order:

1. `AGENTS.md`
2. `README.md`
3. `docs/README.md`
4. `docs/todo-phase-2.md`
5. `docs/phase-2-summary.md`
6. The relevant topic index under `docs/qa/`, `docs/testing/`, `docs/evals/`, or `docs/frontend/`

## Current QA Map

The QA stack is organized as:

```text
translator preprocess
-> high-precision rules
-> router fallback model for ambiguous cases
-> intent-specific handlers
-> SQL / RAG / live_info / weather / navigation / generation
-> answer postprocess
```

Important current boundaries:

- All non-Chinese user queries pivot to Chinese before intent rules run.
- Rules only direct-pass high-confidence cases; uncertain or multi-intent cases go to router fallback.
- SQL is primary for stored attraction/profile facts. RAG is reserved for SQL-uncovered deep questions.
- `live_info` is for same-day official attraction operations and uses a short Redis-backed cache.
- `navigation_text` owns text route planning, slot extraction, Amap calls, multi-leg aggregation, public transit fallback, and place disambiguation.
- Clarification state is typed per intent; each intent owns its own rules and state while sharing the router fallback runtime with type-specific prompts.

## Documentation Workflow

- `README.md` is the global entry point.
- `docs/README.md` is the detailed document index.
- Topic details should live in topic docs, not in the root README.
- When architecture, routing strategy, evaluation direction, testing strategy, or phase-entry structure changes, update the relevant topic doc and refresh the README/docs index in the same pass.
- When work changes project state, update the documentation record in the same pass:
  - [docs/phase-2-summary.md](docs/phase-2-summary.md) for current status and continuation notes.
  - [docs/todo-phase-2.md](docs/todo-phase-2.md) for progress, pending work, and next execution order.
  - [docs/dev-retrospective.md](docs/dev-retrospective.md) only for strategy changes, recurring problems, root-cause analysis, regressions, or decisions with a clear problem / cause / improvement. Do not add a retrospective entry for every small test or routine verification.
