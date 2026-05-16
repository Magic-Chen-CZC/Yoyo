# Yoyo Todo

> Archive note: this file is now the previous-phase todo archive.
> For the current active working set, read `docs/todo-phase-2.md`.
> For the current phase summary, read `docs/phase-2-summary.md`.

This is the active implementation plan for the current integrated branch.

It replaces the older A/B split checklist as the primary working todo.
Current scope is no longer “build missing modules from scratch”; it is:
- lock the first-phase product boundary
- make frontend/backend parallel development possible
- remove deferred route-edit intelligence from QA
- harden manual route editing with runtime-aware constraints
- continue productionization of the SQL-first + RAG-fallback backend

---

## 0. Product decisions locked for the current phase
- [x] Keep the map as a **cognitive map**, not a full rendered map product.
- [x] Keep Amap as a **route engine only**, not the map renderer.
- [x] Keep Guide **SQL-first**, not Guide-RAG.
- [x] Keep QA on **SQL-first + RAG fallback**.
- [x] Keep Guide refresh as one unified user-facing action (`cycle_content`).
- [x] Use guest quick entry + fixed questionnaire as the first-phase onboarding path.
- [x] Keep first-phase itinerary entry types as `template`, `manual_poi`, and `ai_recommendation_selected`.
- [x] Keep explicit trip lifecycle states: `pending`, `active`, `finished`.
- [x] Remove the current “QA changes route” product path and keep **manual route edit only** for now.
- [x] Lock route editing to **unfinished itinerary segments only**:
  - completed stops are frozen
  - the current stop is still editable
  - future stops are editable

---

## 1. What is already complete on this branch

### 1.1 Onboarding and profile setup
- [x] Guest quick-entry API
- [x] Fixed versioned questionnaire flow (`v1`, 7 questions)
- [x] Guide-role choice mapped onto `guide_style_preference`
- [x] Questionnaire submission validation and profile mapping

### 1.2 Planning and route creation
- [x] Itinerary creation supports `template`, `manual_poi`, `ai_recommendation_selected`
- [x] Route template listing
- [x] AI recommendation endpoint
- [x] Manual POI selection input
- [x] Versioned itinerary model with active version switching

### 1.3 Session, GPS, and cognitive map
- [x] `current_stop_index`-based session runtime
- [x] GPS arrival detection with per-stop thresholds
- [x] Playback trigger behavior on arrival
- [x] Stable session current response
- [x] Stable cognitive-map payload with markers/polyline/navigation summary
- [x] Stop knowledge summaries in map payload
- [x] Stop comment stats in map payload

### 1.4 Guide, QA, and content generation
- [x] Async guide generation job path
- [x] SQL-backed multi-segment guide content
- [x] Unified `cycle_content` action for guide refresh
- [x] QA SQL-first + RAG fallback scaffold
- [x] Runtime LLM path for QA and Guide wording
- [x] Live-info provider abstraction and source-bearing responses

### 1.5 Social and sharing
- [x] Stop-level comments API
- [x] Finished-trip share-card aggregation

### 1.6 Ops and evaluation
- [x] RAG rebuild/latest admin endpoints
- [x] LlamaIndex + pgvector scaffold
- [x] Batch eval / judge / comparative reporting baseline

---

## 2. P0 — Current boundary reset and frontend contract closure

### 2.1 Replace the old split-phase working docs with current-phase docs
- [x] Rewrite `docs/todo.md` into the current integrated implementation plan
- [x] Keep `docs/todo.zh-CN.md` aligned with the new todo structure
- [x] Update `README.md` so it points to the current frontend/backend contract docs
- [x] Update `docs/contracts.md` so active contracts match the current product scope
- [x] Update `docs/architecture.md` with the new manual route-edit semantics
- [x] Update `docs/collaboration.md` to remove obsolete A/B route-edit handoff language
- [x] Update `docs/current-session-summary.md` so it no longer presents QA route edit as an active continuation point
- [x] Update `docs/b-stack-implementation-overview.md` so deferred items reflect the new scope

### 2.2 Add a full frontend/backend API definition document
- [x] Add `docs/api-contracts-fullstack.md`
- [x] Document the common API envelope (`code`, `message`, `data`)
- [x] Document all first-phase frontend-consumed endpoints:
  - guest
  - questionnaire
  - planning
  - session
  - gps
  - guide
  - map
  - comments
  - share-card
  - qa
  - rag
- [x] Add request/response examples for each endpoint
- [x] Add state semantics and error behavior for each endpoint
- [x] Add a dedicated route-edit integration section for frontend developers
- [x] Mark which fields are stable contracts vs first-phase provisional fields

### 2.3 Remove the QA route-edit product path
- [x] Remove `planner_handoff` from the active QA runtime path
- [x] Remove `planner_handoff` from QA response metadata
- [x] Remove `planner_handoff`-specific skill/validator/formatter/schema code
- [x] Remove or rewrite QA tests that still expect structured route-edit handoff
- [x] Remove active product docs that still describe QA route editing as part of the current flow

### 2.4 Keep only manual route editing for now
- [x] Make `POST /api/v1/planning/itineraries/{itinerary_id}/edits` the only route-edit entry point in current docs
- [x] Define the current product rule clearly in code and docs:
  - completed stops are frozen
  - current stop editable
  - future stops editable
- [x] Ensure a completed itinerary cannot be edited further

---

## 3. P0 — Runtime-aware manual route editing

### 3.1 Route-edit eligibility rules
- [x] Compute route-edit boundaries from session progress
- [x] Use `current_stop_index` as the primary edit boundary for active trips
- [x] Ensure GPS arrival alone does **not** freeze the current stop
- [x] Ensure playback `complete` / `skip` marks stop progression correctly for editability
- [x] Handle last-stop completion correctly so the final stop becomes non-editable when the trip segment is done

### 3.2 Enforce edit constraints in planning service
- [x] Reject `replace_stop` on completed stops
- [x] Reject `remove_stop` on completed stops
- [x] Reject reorder requests that change the completed route prefix
- [x] Reject `shorten_route` when it would cut off the current stop or completed prefix
- [x] Keep `add_stop` limited to the editable portion of the trip (first-phase default: append to tail)
- [x] Align the public route-edit schema with actual supported operations (including deciding the status of `optimize_route`)

### 3.3 Expose editability to frontend-facing runtime payloads
- [x] Extend `session current` payload with editability fields
- [x] Extend map marker payloads with completed/editable state
- [x] Extend navigation summary with completed/editable boundary information
- [x] Keep session/map/frontend route state consistent after version switches
  - [x] clear stale playback/guide refresh context on active-session version switch
  - [x] make QA reuse session-current route context after version switch
  - [x] add full session/map version-switch consistency assertions

### 3.4 Preserve versioning and session remap behavior
- [x] Keep route edits version-based rather than in-place mutation
- [x] Preserve current-stop remap when the current editable stop changes
- [x] Reset playback state when the active current stop changes after edit
- [x] Keep completed prefix stable across route edits

---

## 4. P1 — QA/Guide productionization after the boundary reset

### 4.1 Remove hardcoded QA fallback behavior in user-facing paths
- [x] Replace `translation` phrase-map fallback with runtime-LLM-first behavior + explicit degraded responses
- [x] Replace deterministic `trip_assistant` fallback templates with stronger route-aware generation + degraded behavior
- [x] Remove transitional user-facing wording from `attraction_explain`
- [x] Make `live_info` return explicit unavailable/degraded responses when config/upstream fails
- [x] Tighten attraction/profile fallback so production-oriented paths do not silently mix mock data

### 4.2 Structured output and post-processing hardening
- [x] Add structured-output validation for runtime QA responses
  - [x] first step: translation structured-output parsing + validation
  - [x] first step: live_info structured-output parsing + validation
  - [x] align `trip_assistant` structured schema + JSON-only prompt contract
  - [x] align `attraction_explain` structured schema + JSON-only prompt contract
  - [x] wire `trip_assistant` generator/orchestrator/validator structured-output handling
  - [x] wire `attraction_explain` generator/orchestrator/validator structured-output handling
  - [x] add targeted valid/malformed structured-output tests for both intents
- [x] Add structured-output validation for runtime Guide responses
  - [x] add internal Guide bundle schema + generator-level structured validation
  - [x] make guide generation consume only validated LLM bundle output before fallback builder merge
  - [x] add focused valid/malformed Guide runtime tests
- [x] Add safer post-processing for malformed LLM output
  - [x] add shared lightweight sanitize helper for user-visible LLM text
  - [x] sanitize QA structured answers before returning them
  - [x] sanitize Guide bundle text fields before builder merge/fallback selection
  - [x] remove Guide high-risk first/last brace JSON rescue in favor of stricter fenced-object parsing
  - [x] add focused malformed post-processing tests for QA and Guide
- [x] Keep degraded-mode responses explicit rather than placeholder-like
- [x] Define a minimal-impact QA structured-output plan for:
  - `translation`
  - `live_info`
  - `trip_assistant`
  - `attraction_explain`
  while keeping the user-facing `answer` field free-form and using structured fields only for backend validation/state

### 4.3 Guide content and asset productionization
- [x] Improve `cycle_content` selection using:
  - `answer_length_preference`
  - `interests`
  - `guide_style_preference`
- [x] Decide whether frontend should receive “remaining content” counters
  - current decision: frontend does not need a displayed remaining-content count; keep `more_content_available` as the user-facing signal for this phase
- [x] Replace `audio` placeholder semantics with a real TTS/media asset flow
  - current decision: connect one real TTS model, with API key configured later
  - latency requirement: do not block each `cycle_content` click on full-stop audio generation; prefer prioritized current-stop / current-batch generation and async background completion

---

## 5. P1 — QA RAG productionization
- [x] Complete backend-enabled pgvector retrieval in a real configured environment
  - verified locally with pgvector-enabled PostgreSQL, successful rebuild/latest responses, and ready backend state after fixing migration and PGVectorStore runtime compatibility issues
- [x] Validate embedding -> indexing -> query end-to-end
  - verified end-to-end through rebuild -> latest -> deep `/api/v1/qa/ask`; QA metadata now shows `retrieval_strategy = sql_then_rag`, `rag_backend_ready = true`, and `rag_query_status = ok`
- [x] Harden ingestion lifecycle and rebuild behavior
- [x] Clarify operational rebuild/index-run semantics for admins
- [x] Ensure QA metadata reflects real retrieval state correctly in configured and degraded modes

---

## 6. P1 — Test and verification hardening

### 6.1 Route/session/map verification
- [x] Add tests proving completed stops cannot be edited
- [x] Add tests proving the current stop can still be edited
- [x] Add tests proving reorder can only touch the editable suffix
- [x] Add tests proving last-stop completion freezes the remaining route
- [x] Add tests for session current editability fields
- [x] Add tests for map marker completed/editable fields

### 6.2 QA/Guide failure-mode coverage
- [x] Add module-level tests for `qa`, `knowledge`, `live_info`, `guide`, and runtime-LLM post-processing
- [x] Add degradation/failure-mode tests for:
  - [x] missing provider config
  - [x] LLM failure
  - [x] malformed structured output
  - [x] missing real data
  - [x] upstream provider errors

### 6.3 End-to-end integration flows
- [x] Add integration flow: itinerary -> guide job -> GPS/playback -> session current/map
- [x] Add integration flow: manual route edit -> version switch -> session remap -> map/session consistency
- [x] Add integration flow: session-aware QA after route/session state changes
- [x] Make benchmark runs fail fast or mark invalid when required API keys are missing
  - missing-key behavior is now explicit in eval providers/batch execution; broader benchmark test redesign is deferred to a later pass
- [x] Refresh demo testing docs for current product boundary
  - updated `docs/test-readiness-checklist.md` and `docs/demo-test-plan.md` with guide jobs, RAG latest 404 semantics, finished-session boundaries, QA out-of-scope, route-edit 422, and share-card consistency checks
- [x] Prepare Feishu-facing demo test explanation doc
  - added `docs/feishu-demo-test-cases.md` and imported it to Feishu for product/test use
- [x] Resolve current regression failures found by the refreshed P0 pytest suite
  - aligned guide/QA tests with current runtime semantics (TTS pending vs unavailable, configurable voice, provider-driven QA wording, and session-context assertions) and re-ran the consolidated regression suite successfully
- [x] Run real API smoke verification against local service stack
  - verified `health`, `rag latest/rebuild/latest`, real itinerary/session/map/qa/share-card flow, and real guide worker -> job -> asset -> content path; also documented the new operational prerequisite that guide asset/content smoke tests require the worker process (`.venv/bin/arq yoyo.jobs.worker.WorkerSettings`) in addition to the API server
- [x] Harden weather target fallback coverage
  - added/validated targeted QA coverage for `weather_info` fallback extraction and itinerary-city defaulting, including builder-level `rule -> fallback -> default city` behavior and API-level session-aware fallback to itinerary `city_code`; current targeted run is `pytest tests/test_qa.py -k "weather" -v` -> `3 passed`
- [x] Run real degraded-mode smoke verification
  - verified `RAG_ENABLED=false` returns `rebuild -> skipped/rag_disabled`; QA can still answer from SQL grounding with `rag_backend_ready = false` and `rag_query_status = skipped`; documented that degraded guide validation requires API and worker to share the same env, otherwise asset-level audio state can reflect worker config rather than the API instance under test
- [x] Run real live-info provider-failure smoke verification
  - verified that missing Tavily config yields `live_info -> status=unavailable`, `reason=missing_provider_config`, `degraded=true`, `confidence=low`, source marker `tavily_missing_key`, and a user-facing answer that explicitly redirects users to official/reliable same-day sources
- [x] Refresh Feishu-facing demo test explanation with real verification findings
  - re-imported the Feishu doc after adding real smoke/degraded findings for guide worker prerequisite, asset/content audio semantics, RAG disabled behavior, and live_info provider-failure behavior
- [x] Design the next test round as a pre-release risk pass
  - documented the next-round focus in `docs/demo-test-plan.md` and `docs/test-readiness-checklist.md`: deployment consistency, external dependency fault injection, state-transition regressions, and performance/latency checks
- [x] Build and run a QA benchmark for `google/gemini-2.5-flash-lite`
  - added a 180-question QA benchmark dataset under `evals/datasets/qa_benchmark_gemini_flash_lite_180.yaml` (6 buckets × 30 questions) plus per-bucket part files and a 30-question smoke subset; ran the benchmark via OpenRouter using `google/gemini-2.5-flash-lite`, generated results/scores/summary JSON, and exported the accumulated eval workbook to `evals/results/benchmark_results.xlsx`
- [x] Persist test rounds as Excel + Feishu documentation
  - added `docs/test-rounds-log.md`, created `/Users/czc/vscode/Yoyo/evals/results/test_rounds.xlsx` as a round-level test ledger, and imported a dedicated Feishu test-rounds document for ongoing recording
- [x] Re-run the 180-question QA benchmark for additional candidate models in parallel
  - completed parallel runs for `openai/gpt-5.4-nano` and `google/gemini-2.5-flash` via OpenRouter, refreshed `evals/results/benchmark_results.xlsx`, and appended the detailed latency/cost/completion findings to `docs/test-rounds-log.md`
- [x] Add a true E2E QA benchmark track
  - added `docs/e2e-qa-benchmark.md`, extended `docs/eval-fields.md`, clarified benchmark layering in readiness/demo docs, created `evals/results/e2e_qa_benchmark.xlsx`, executed baseline `/api/v1/qa/ask` runs in standard and degraded environments, and created a dedicated Feishu E2E QA benchmark ledger
- [x] Reframe E2E QA case design around current seed-backed data reality
  - updated `evals/datasets/e2e_qa_benchmark_cases.json` and `docs/e2e-qa-benchmark.md` so current cases are explicitly tagged as `chain_validity` or `seed_plausibility`, avoiding accidental claims about real-world content accuracy while attraction/profile/RAG data is still seed/mock based
- [x] Narrow live-info scope to official attraction-site information only
  - updated routing and documentation so current `live_info` covers official attraction notices, opening/booking/closure information only; weather, traffic, and crowd conditions are explicitly deferred to dedicated APIs and excluded from ordinary web search
- [x] Consolidate E2E benchmark assets and enrich the case dataset
  - moved benchmark fixtures into `evals/datasets`, moved benchmark reports into `evals/results`, expanded `evals/datasets/e2e_qa_benchmark_cases.json` with operation/query_zh/profile/fixture/assertion fields, and extended `evals/export_excel.py` to export `e2e_cases` and `e2e_summary` sheets
- [x] Run the new three-model E2E QA benchmark and export Excel
  - added `evals/run_e2e_qa_benchmark.py`, added `src/yoyo/scripts/seed_benchmark_fixtures.py`, seeded benchmark fixtures into PostgreSQL, ran E2E QA benchmark for `openai/gpt-5.4-nano`, `google/gemini-2.5-flash`, and `google/gemini-2.5-flash-lite`, and exported the combined workbook to `evals/results/e2e_qa_benchmark_run_v2.xlsx`
- [x] Upgrade QA prompt to v2 and add a prompt debugging note
  - rewrote `src/yoyo/modules/qa/prompts.py` to better separate attraction explain / live_info / out_of_scope boundaries, allow light travel-adjacent chit-chat, switch prompt versioning to `qa-{intent}-v2`, and added `docs/qa-prompt-debugging.md` for continued prompt iteration
- [x] Re-run the three-model E2E benchmark after prompt v2
  - restarted dedicated API instances for `openai/gpt-5.4-nano`, `google/gemini-2.5-flash`, and `google/gemini-2.5-flash-lite` on fresh ports, re-ran the same 23-case E2E QA dataset, and exported the new workbook to `evals/results/e2e_qa_benchmark_run_v3_prompt_v2.xlsx`
- [x] Fix QA routing root causes and document the attribution
  - repaired `domain_guard`, `intent_router`, and `orchestrator` so Chinese attraction queries and travel-adjacent boundary questions are no longer over-blocked or uniformly rejected, added focused regression tests, and documented the root cause in `docs/qa-routing-root-cause-and-fix.md`
- [x] Re-run the three-model E2E benchmark after system-layer fixes
  - restarted dedicated API instances for `openai/gpt-5.4-nano`, `google/gemini-2.5-flash`, and `google/gemini-2.5-flash-lite` on fresh ports, re-ran the same 23-case E2E QA dataset after routing fixes, and exported the new workbook to `evals/results/e2e_qa_benchmark_run_v4_system_fix.xlsx`
- [x] Add hybrid routing plan: rules first + small-model fallback
  - implemented the rule-layer contract in QA routing: `domain_guard` now acts as hard-deny-only, `intent_router` now returns full routing metadata (`intent`, `margin`, `needs_fallback`, `fallback_reason`, boundary subtype), and `manual_route_edit_redirect` is now a first-class intent instead of a trip_assistant sub-branch
- [x] Design a routing-model benchmark and candidate sweep
  - added `evals/datasets/routing_benchmark_cases.json`, `evals/run_routing_benchmark.py`, `evals/run_routing_candidate_sweep.py`, and `evals/routing_candidates.yaml` for router-only evaluation of `domain_guard -> intent_router -> optional router_fallback`; smoke outputs now land under `evals/results/routing_*`, Excel export includes routing sheets, and the old `planner_handoff` benchmark label was normalized to `manual_route_edit_redirect` in the active route-edit benchmark part file
  - completed a first lexicon-expansion pass in `src/yoyo/modules/qa/intent_router.py` with paired regression/benchmark cases for translation, route-edit, trip-assistant, and attraction-explain phrase variants; the rule layer was kept intentionally looser so ambiguous queries can still fall through to fallback, and the updated rules-only router benchmark improved from 11/14 to 18/22 while keeping boundary accuracy at 1.0
  - added `evals/datasets/routing_benchmark_100_cases.json` as a broader end-to-end router-only test set with 100 labeled cases (including easy/confusable/out-of-scope samples), then ran full-module routing evaluation: `rules_only_100` reached 75/100 = 0.75 accuracy and `rules_plus_fallback_gpt54nano_100` reached 85/100 = 0.85 accuracy, showing clear gains from the looser-rules-plus-fallback strategy
  - later phase-2 routing hardening continued in `docs/todo-phase-2.md`; latest keyed zh-hard v2 rerun there has reached `rules_plus_fallback_qwen_flash=1.0` and `rules_plus_fallback_qwen_turbo=0.9861`, with same-round `routing_pure_fallback_qwen_turbo=0.9861` as the control
- [x] Add Southeast Asia multilingual routing evaluation plan
  - current plan is to cover Thai, Vietnamese, Indonesian, Malay, and Filipino first, but the working product decision is now to send all queries through a translator first, normalize them into Chinese, and then run the same rules + classifier intent module before downstream pipeline routing
- [x] Align the minimum handoff docs and README entrypoint rule
  - updated `CLAUDE.md`, `README.md`, `docs/todo.md`, `docs/collaboration.md`, and `docs/current-session-summary.md` so the default minimum resume set is now `CLAUDE.md`, `README.md`, and `docs/todo.md`, with README acting as the canonical entrypoint for architecture/framework/routing/evaluation docs

---

## 7. P2 — Later product work after current closure
- [ ] Replace the fixed starter planner source with a more realistic planner source when planning scope resumes
- [ ] Decide whether multi-turn QA should remain recent-turn-only or add conversation summaries
- [ ] Revisit whether route-edit assistance should return to QA later as a new scoped feature, only after manual route editing is stable and fully verified

## 7.1 Current documentation consolidation
- [x] Add a dedicated frontend docs entry under `docs/frontend/`
- [x] Refresh `docs/api-contracts-fullstack.md` so implemented frontend fields match current code
- [x] Update `README.md` and related docs to point frontend development to the consolidated entry and avoid duplicate contract details

---

## 8. Current recommended execution order
1. Rewrite active docs (`todo`, `contracts`, `architecture`, `README`, collaboration docs)
2. Add the full frontend/backend API contract document
3. Remove QA route-edit runtime behavior
4. Implement manual route-edit freezing rules
5. Expose editability state in session/map payloads
6. Add/repair tests for the new route-edit semantics
7. Continue QA/Guide/RAG productionization work

---

## 9. Working rule for future sessions
- The default minimum resume set should be: `CLAUDE.md`, `README.md`, and `docs/todo.md`.
- README must remain the canonical entrypoint for current architecture/framework/routing/evaluation documents.
- Whenever architecture, framework, routing strategy, or evaluation direction changes, update the relevant docs and refresh the README entry in the same pass.
- Also update `docs/current-session-summary.md` whenever major discussions, decisions, or implementation-direction changes happen, so the session log stays current even though it is not part of the minimum resume set.
- Use `docs/demo-test-plan.md` when preparing product/demo validation instead of reconstructing a new test matrix from scratch.
- Do not reintroduce QA route-edit execution into the current product path unless the product decision changes.
- After each completed implementation part, update this todo before continuing.
- 2026-05-15 补记：QA `context_build_ms` 已拆出 `context_build_breakdown_ms`，当前可直接观察 attraction/profile/live/weather/navigation/rag/prompt projection 等子步骤耗时，用于继续排查天气与导航链路的额外时延。
- 2026-05-15 再补记：天气链路已收口为“规则先判天气且成功抽到地点才跳过 fallback；否则由 router fallback 一次同时产出 intent + `weather_location_name`，context build 直接复用该地点，不再额外发起第二次 weather slot fallback 模型调用”。对应定向回归：`pytest tests/test_qa.py -k "weather or router_fallback" -vv`（9 passed）、`pytest tests/test_routing_benchmark.py -vv`（6 passed）。
