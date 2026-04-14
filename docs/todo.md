# Yoyo Todo

This is the active todo list after splitting work into A/B tracks.

---

## Shared / coordination
- [x] Write shared overlap contracts into `docs/contracts.md`
- [x] Freeze shared `itinerary_version.plan_json` contract in `docs/architecture.md`
- [x] Freeze shared `guide_generation_job.result_json` contract in `docs/architecture.md`
- [x] Freeze shared `guide_session.context_json` field ownership in `docs/architecture.md`
- [x] Freeze `session current` response contract in `docs/architecture.md`
- [x] Define GPS -> guide trigger handoff behavior in `docs/architecture.md`
- [x] Define `planner_handoff` structured payload contract in `docs/architecture.md`
- [x] Decide migration ownership rule for the next schema changes
- [x] Keep `api/router.py` wiring changes small and late
- [x] Finish all remaining shared contracts above before broad QA verification

---

## A track: Planner / Session / Map / GPS

### A1. Route editing and version management
- [x] Add route edit request schema
- [x] Implement replace stop operation
- [x] Implement remove stop operation
- [x] Implement reorder stop operation
- [x] Implement shorten route operation
- [x] Create new `itinerary_version` on each edit
- [x] Switch active itinerary version after edit
- [x] Keep prior versions queryable
- [x] Add tests for version switching

### A2. Session runtime state
- [x] Add `current_stop_index` to session runtime model
- [x] Stop assuming current stop is always the first stop
- [x] Compute current stop from session state
- [x] Compute next stop from session state
- [x] Add tests for session progression

### A3. GPS and geofence
- [x] Add first distance calculation helper
- [x] Add per-stop arrival threshold
- [x] Mark arrived when user enters threshold
- [x] Update session runtime when arriving at a stop
- [x] Prepare trigger signal for guide playback
- [x] Add tests for geofence logic

### A4. Map payload improvements
- [x] Guarantee stable marker fields
- [x] Guarantee stable polyline fields
- [x] Align current/next stop with `current_stop_index`
- [x] Expose frontend-friendly navigation summary
- [x] Add map payload tests

### A5. Contract hygiene
- [x] Ensure every stop has `name/category/latitude/longitude/recommended_duration_minutes`
- [x] Update `docs/architecture.md` when stop contract changes

---

## B track: Guide / QA / Retrieval / Eval

### B1. QA quality upgrades
- [x] Make `planner_handoff` return structured route-edit intent
- [x] Strengthen `trip_assistant` route-aware answers
- [x] Strengthen `attraction_explain` answer formatting
- [x] Improve `translation` outputs beyond placeholder mode
- [x] Add category-specific answer formatting tests

### B2. Live-info provider integration
- [x] Introduce live-info provider abstraction
- [x] Add provider-backed source records
- [x] Preserve `updated_at` and source metadata in responses
- [x] Add graceful failure / not-confirmed behavior
- [x] Add tests for source-bearing live-info responses

### B3. Guide generation enrichment
- [x] Expand `result_json` to include guide script payload
- [x] Expand `result_json` to include card payload
- [x] Prepare TTS-ready output fields
- [x] Add tests for enriched guide generation output

### B4. Playback and guide asset improvements
- [x] Connect gps trigger action to playback transitions
- [x] Add `trigger` flow coverage in tests
- [x] Add richer playback metadata in session context
- [x] Ensure active guide asset always reflects latest successful version

### B5. Model evaluation improvements
- [x] Batch query generation
- [x] Multi-provider eval runner
- [x] Cost/latency summary
- [x] Basic rubric scoring
- [x] Batch multi-model run support
- [x] English 81-query dataset
- [x] Add stronger rubrics per category
- [x] Add comparative markdown report generation
- [x] Add category breakdown report
- [x] Add per-model ranking output
- [x] Run first real benchmark on selected models

### B6. First real benchmark execution
- [x] Prepare `.env` with provider keys
- [x] Confirm first benchmark matrix
- [x] Run English 81-query batch for shortlisted models
- [x] Save results to `evals/results/`
- [x] Summarize latency/cost/score comparison

---

## B track: SQL-first completion phase
- [x] Adopt PostgreSQL as the SQL-first knowledge store for B stack
- [x] Seed 50 mock PostgreSQL records for attractions and user profiles
- [x] Add shared SQL-first knowledge layer for QA and Guide generation
- [x] Add PostgreSQL seed script and make retrievers prefer database reads with mock fallback
- [x] Move attraction knowledge from static catalog to PostgreSQL-backed retrieval
- [x] Add profile-aware guide generation
- [x] Add hybrid retrieval for QA (SQL + live info)
- [x] Connect `qa_messages` into multi-turn QA memory
- [x] Extend planner_handoff extraction coverage
- [x] Enrich guide generation output with per-stop script content
- [x] Upgrade playback metadata while keeping A/B ownership boundaries stable
- [x] Update eval architecture to reflect the SQL-first phase
- [x] Update README with the current SQL-first local run flow and seed step
- [x] Add a compact round-1 model-selection test case document for B track
- [x] Add round-1 model shortlist and test-case field definitions to the selection doc
- [x] Add execution order and per-case result template to the round-1 model-selection doc
- [x] Add a dedicated round-1 model matrix and executable dataset for automated evaluation
- [x] Document prompt-safe SQL field exposure boundaries for future real-data integration
- [x] Add prompt-safe projection rules to code and introduce guide style preference control
- [x] Add a shared runtime LLM layer for product QA and Guide generation
- [x] Connect Guide generation text fields to runtime LLM with deterministic fallback
- [x] Connect QA attraction/trip/live/translation responses to runtime LLM with rule fallback
- [x] Fix project-root .env loading so eval and runtime model calls can read configured keys reliably
- [x] Re-run round1 model evaluation with real key loading and export final Excel
- [x] Add a focused round-2 Gemini test-case document based on round1 findings
- [x] Add executable Gemini round-2 model matrix and dataset files
- [x] Expand Gemini round-2 dataset to ~200 queries with judge-friendly metadata
- [x] Add hard-check scoring structure before judge integration
- [x] Add gpt-5.4-mini judge path and judge result artifacts
- [x] Extend reporting and Excel export for rule + judge results
- [x] Add a Chinese reference version of the todo document for Feishu/internal sharing

## Current recommendation
- A continues on route/runtime state and version progression
- B is now in a SQL-first completion phase
- Current phase uses PostgreSQL for attraction/profile knowledge and keeps live search only for real-time changes
- RAG is deferred for now and can be added later if SQL-backed knowledge becomes insufficient
- After each completed B implementation part, update this todo before continuing
