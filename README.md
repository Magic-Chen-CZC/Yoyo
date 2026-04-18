# Yoyo

Backend-first FastAPI project for the Yoyo Beijing tour intelligent guide system.

## Current scope
- Modular monolith backend
- Planner module
- Controlled single-agent Guide QA module
- PostgreSQL + Redis
- Versioned itineraries and async guide generation jobs
- Guest-first onboarding for the first phase (quick guest entry before full auth)
- Questionnaire-driven profile building with a guide-role choice mapped onto `guide_style_preference`
- Travel selection now starts expanding toward three entry modes: route templates, manual POI selection, and AI recommendation selection
- The map layer is currently a cognitive map / route state payload rather than a full real-world base map integration
- Amap is now used only as a route-engine integration point for stop ordering/polyline calculation, not as the rendering map itself
- Current B-side implementation is SQL-first for attraction/profile knowledge, with QA now starting to add a first-phase SQL-first + RAG fallback scaffold
- Guide remains SQL-first and now begins moving toward multi-segment attraction content stored in SQL rather than Guide-side RAG
- Live search is currently reserved for real-time travel changes

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
8. Optional: prepare the first-phase RAG scaffold:
   - enable pgvector via migrations
   - set `rag_enabled=true`, `rag_pgvector_dsn`, `rag_embedding_api_key`, `rag_embedding_base_url`, and `rag_embedding_dimension` in `.env`
   - current local recommendation: `rag_pgvector_dsn=postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/yoyo`
   - run `PYTHONPATH=src .venv/bin/python src/yoyo/scripts/build_rag_index.py`
9. Optional: prepare real TTS validation for Guide audio:
   - set `tts_provider=dashscope`, `tts_base_url`, `tts_api_key`, and `tts_voice` in `.env`
   - optionally set `tts_model`, `tts_audio_format`, and `tts_storage_dir`
   - then use `POST /api/v1/guide/content/{guide_session_id}` to validate current-batch audio generation

Note:
- Config now loads `.env` from the project root, so scripts can still read keys correctly even when launched from outside the repo directory as long as `PYTHONPATH=src` is set.

## Development notes
- API prefix: `/api/v1`
- Source code lives in `src/yoyo`
- Tests live in `tests`
- First-phase onboarding endpoints now include:
  - `POST /api/v1/guest/sessions`
  - `GET /api/v1/questionnaire/flows/current`
  - `POST /api/v1/questionnaire/submissions`
- Planning now starts exposing first-phase selection helpers:
  - `GET /api/v1/planning/templates`
  - `POST /api/v1/planning/recommendations`
- Session lifecycle now includes explicit travel actions:
  - `POST /api/v1/session/guide/{guide_session_id}/start`
  - `POST /api/v1/session/guide/{guide_session_id}/finish`
- Stop comments and cognitive-map enrichment endpoints now include:
  - `GET /api/v1/map/session/{guide_session_id}` with stop knowledge summaries and comment stats
  - `GET /api/v1/comments/stops/{stop_id}`
  - `POST /api/v1/comments/stops/{stop_id}`
- Share-card endpoint now includes:
  - `GET /api/v1/share-card/session/{guide_session_id}`
- Guide content cycling endpoint now includes:
  - `POST /api/v1/guide/content/{guide_session_id}` with the unified `cycle_content` action
- RAG admin endpoints now include:
  - `POST /api/v1/rag/index-runs/rebuild`
  - `GET /api/v1/rag/index-runs/latest`
- The rebuild endpoint supports first-phase selective requests such as `poi_name`, `doc_type`, `language`, `use_seed`, and `limit`, so mock-data flows can be exercised before full backend config is enabled.
- Project continuity notes live in `CLAUDE.md`
- Architecture notes live in `docs/architecture.md`
- Working todo lives in `docs/todo.md`
- Frontend/backend API contracts live in `docs/api-contracts-fullstack.md`
- Collaboration split lives in `docs/collaboration.md`
- Shared overlap contracts live in `docs/contracts.md`
- Model evaluation plan lives in `docs/model-evaluation.md`
- Teammate setup guide lives in `docs/dev-setup-for-teammates.md`
- Current B-side implementation overview lives in `docs/b-stack-implementation-overview.md`
- Future real-data / RAG / TTS preparation checklist lives in `docs/b-stack-preparation-checklist.md`
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
- QA now has a first-phase SQL-first + RAG fallback path; when pgvector/LlamaIndex is configured, QA can prefer vector-query results for deeper attraction explanation cases
- QA is not the current route-edit entry point; route edits are handled manually through the planning edit API.
- Guide remains SQL-first: attraction records can now evolve toward richer multi-segment SQL content so the main tour flow does not depend on RAG.
- a shared runtime LLM layer now exists for product QA and Guide generation text generation

## Runtime LLM generation notes
- Shared runtime provider wiring now lives under `src/yoyo/modules/llm/`.
- This layer is intended for product QA and Guide generation runtime calls, not only evaluation scripts.
- Current default runtime recommendation is `openrouter` with `google/gemini-2.5-flash-lite`.
- Product code should use the runtime layer instead of calling eval providers directly.
- Guide generation now attempts runtime LLM generation for guide text fields and falls back to the deterministic builder if the LLM call fails.
- QA now attempts runtime LLM generation for attraction explanation, trip assistant, translation, and live-info wording, while keeping rules-first routing and fallback output.
- QA retrieval is now beginning to add a first-phase RAG scaffold: SQL facts remain primary, and retrieved chunks are attached as supporting context for deeper attraction explanation cases.
- The intended and now partially wired RAG stack is LlamaIndex + pgvector. The system can already prepare documents, build an index path, and prefer pgvector query results when the backend is configured, while still degrading safely when it is not.

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
