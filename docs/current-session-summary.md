# Current Session Summary

This document summarizes the major product/backend changes completed in the current Claude session so the next session can continue without re-discovering context.

## 1. Product direction confirmed in this session

### Onboarding / identity
- First phase uses **guest quick entry** rather than full auth.
- The user picks a **guide role**, but this is currently mapped onto `guide_style_preference` rather than a separate role system.
- The onboarding questionnaire is now a fixed, versioned, choice-based flow.

### Travel selection
- Planner now supports first-phase entry modes:
  - `template`
  - `manual_poi`
  - `ai_recommendation_selected`
- These are still first-phase backend scaffolds, not the final full planner experience.

### Map direction
- The map is explicitly treated as a **cognitive map**, not a real map product.
- Amap is only used as a **route engine** for order/polyline calculation, not as the rendering map itself.

### QA / Guide knowledge strategy
- **QA**: SQL-first + first-phase RAG fallback path.
- **Guide**: keep SQL-first; do **not** make Guide depend on RAG.
- The user explicitly decided Guide should rely on richer SQL content instead of Guide-side RAG.

### Guide UX decision
- Guide content is short because of audio playback constraints.
- From the user perspective, there should be only **one** “more/change content” action.
- Backend action is now unified as `cycle_content`.

---

## 2. Main implementation completed in this session

### 2.1 Guest onboarding
Added guest quick-entry and questionnaire/profile mapping.

Key work:
- Guest session API
- Fixed questionnaire flow (`v1`, 7 questions)
- Guide-role choice mapped to `guide_style_preference`
- Questionnaire submission now validates answers and updates `UserProfile`

Key files:
- `src/yoyo/db/models/guest.py`
- `src/yoyo/modules/guest/*`
- `src/yoyo/api/v1/guest.py`
- `src/yoyo/modules/questionnaire/flow.py`
- `src/yoyo/modules/questionnaire/profile_mapper.py`
- `src/yoyo/modules/questionnaire/schemas.py`
- `src/yoyo/modules/questionnaire/service.py`
- `src/yoyo/api/v1/questionnaire.py`
- `alembic/versions/0004_add_guest_users_and_profile_sources.py`

---

### 2.2 Planning entry modes
Expanded itinerary creation toward the first-phase travel selection flows.

Key work:
- Added route templates
- Added recommendation endpoint
- Added manual POI entry support
- Planner input now tracks `entry_type`, `template_id`, `selected_poi_ids`

Key files:
- `src/yoyo/modules/planner/template_repository.py`
- `src/yoyo/modules/planner/recommendation_service.py`
- `src/yoyo/modules/planner/recommendation_schemas.py`
- `src/yoyo/modules/planner/poi_selector.py`
- `src/yoyo/modules/planner/plan_builder.py`
- `src/yoyo/modules/planner/schemas.py`
- `src/yoyo/modules/planner/service.py`
- `src/yoyo/api/v1/planning.py`

---

### 2.3 Session lifecycle
Added explicit trip start / finish semantics.

Key work:
- `GuideSessionStatus` now includes `PENDING`, `ACTIVE`, `FINISHED`
- Added start / finish APIs
- Session context records `trip_state`, `trip_started_at`, `trip_finished_at`

Key files:
- `src/yoyo/modules/shared/enums.py`
- `src/yoyo/db/models/session.py`
- `src/yoyo/modules/session/schemas.py`
- `src/yoyo/modules/session/service.py`
- `src/yoyo/api/v1/session.py`
- `alembic/versions/0005_add_pending_guide_sessions.py`

Note:
- Lifecycle semantics now exist, but some runtime paths remain intentionally backward-compatible.

---

### 2.4 Planner route engine and Amap integration point
Added route optimization hooks and an Amap-backed route engine skeleton.

Key work:
- Added `add_stop`
- Added route optimization hook
- Added route engine / Amap client
- Planner now writes `route_meta` and `polyline`
- Degraded fallback works when no Amap key is configured

Key files:
- `src/yoyo/modules/planner/optimization_service.py`
- `src/yoyo/modules/planner/route_engine.py`
- `src/yoyo/modules/integrations/amap/client.py`
- `src/yoyo/modules/planner/service.py`
- `src/yoyo/modules/planner/schemas.py`
- `tests/test_amap_route_engine.py`

---

### 2.5 Cognitive map enrichment
The map payload now carries stop knowledge summaries and comment stats.

Key work:
- Added stop summary builder
- Map marker/current_stop now include summary/highlights/tips/source/comment stats
- Map can read route polyline from plan

Key files:
- `src/yoyo/modules/knowledge/stop_summary_builder.py`
- `src/yoyo/modules/map/schemas.py`
- `src/yoyo/modules/map/service.py`
- `src/yoyo/api/v1/map.py`

---

### 2.6 Stop comments
Added first-phase stop-level comments / review module.

Key work:
- Comment model
- Comment API create/list
- Map aggregates comment count and latest preview

Key files:
- `src/yoyo/db/models/comment.py`
- `src/yoyo/modules/comments/*`
- `src/yoyo/api/v1/comments.py`
- `alembic/versions/0006_add_poi_comments.py`

---

### 2.7 Share card aggregation
Added a dedicated share-card read model instead of reusing guide asset directly.

Key work:
- New share-card schema/service/API
- Aggregates:
  - finished session lifecycle
  - latest ready guide card content
  - itinerary / plan summary
  - cognitive map preview
  - comment statistics
- Unfinished sessions return `is_shareable = false`

Key files:
- `src/yoyo/modules/share_card/*`
- `src/yoyo/api/v1/share_card.py`
- `src/yoyo/api/router.py`
- `tests/test_share_card.py`

---

### 2.8 QA RAG path
QA now has a first-phase SQL-first + RAG fallback path.

Key work:
- Extended `HybridContext` with `rag`
- Added RAG retrieval guard and fallback router
- QA prompts now accept SQL + RAG supporting context
- QA metadata now traces retrieval strategy and backend/query state

Key files:
- `src/yoyo/modules/knowledge/fallback_router.py`
- `src/yoyo/modules/knowledge/rag_retriever.py`
- `src/yoyo/modules/knowledge/hybrid_context_builder.py`
- `src/yoyo/modules/knowledge/schemas.py`
- `src/yoyo/modules/qa/prompts.py`
- `src/yoyo/modules/qa/orchestrator.py`

---

### 2.9 LlamaIndex + pgvector backend scaffolding and ops
RAG is no longer just a prompt-level placeholder; it now has backend/readiness/index/query/admin scaffolding.

Key work:
- Added config for RAG backend
- Added LlamaIndex + pgvector dependencies
- Enabled pgvector migration
- Added document builders
- Added index service and query path
- Added index script
- Added `RAGIndexRun` model + admin APIs
- Added selective/mock-friendly rebuild request support:
  - `poi_name`
  - `doc_type`
  - `language`
  - `use_seed`
  - `limit`

Key files:
- `src/yoyo/core/config.py`
- `pyproject.toml`
- `alembic/versions/0007_enable_pgvector_extension.py`
- `src/yoyo/modules/knowledge/rag_backend.py`
- `src/yoyo/modules/knowledge/rag_documents.py`
- `src/yoyo/modules/knowledge/rag_index_service.py`
- `src/yoyo/modules/knowledge/rag_admin_service.py`
- `src/yoyo/modules/knowledge/rag_admin_schemas.py`
- `src/yoyo/api/v1/rag.py`
- `src/yoyo/db/models/rag.py`
- `alembic/versions/0008_add_rag_index_runs.py`
- `src/yoyo/scripts/build_rag_index.py`

Important status:
- QA can already prefer pgvector query results **if** backend is configured.
- Without config, the system safely degrades and still supports mock-data flows.

---

### 2.10 Guide SQL-first multi-segment content
Guide was explicitly kept SQL-first. Attraction records now store richer multi-segment guide content for guide playback/refresh.

Key work:
- Added `guide_segments_json` to attraction model
- Mock seed now generates 10+ guide segments per attraction
- Seed script writes guide segments to DB
- Guide generation now consumes multi-segment SQL content

Key files:
- `src/yoyo/db/models/attraction.py`
- `alembic/versions/0009_add_guide_segments_to_attractions.py`
- `src/yoyo/modules/knowledge/seed_postgres.py`
- `src/yoyo/scripts/seed_mock_knowledge.py`
- `src/yoyo/modules/knowledge/sql_retriever.py`
- `src/yoyo/modules/knowledge/schemas.py`
- `src/yoyo/modules/guide/content_builder.py`
- `tests/test_guide_sql_segments.py`
- `tests/test_guide_job_runtime.py`

Important design decision:
- Base attraction data and Guide SQL content currently live in the **same attraction record**, separated by fields, not by separate tables.

---

### 2.11 Unified Guide content cycle
The user decided “再讲一点 / 换一个” should be one user-facing capability, not two separate ones.

Implemented as:
- `action = cycle_content`
- backend decides how to continue within the current stop without advancing route state

Key work:
- Added guide content cycle schema/API
- Added stop-level content cursor/history in `guide_session.context_json`
- Cycle logic works on current stop only
- It does not advance `current_stop_index`
- Finished sessions reject guide content cycling

Key files:
- `src/yoyo/modules/guide/schemas.py`
- `src/yoyo/modules/guide/asset_service.py`
- `src/yoyo/api/v1/guide.py`
- `tests/test_guide_content_cycle.py`

Runtime state used:
- `stop_segment_cursor_by_stop_id`
- `played_segment_indices_by_stop_id`
- `last_refresh_action`
- `last_refresh_at`

---

### 2.12 QA structured-output expansion for trip_assistant / attraction_explain
The current session completed the next QA structured-output step for the remaining runtime intents.

Completed in this work item:
- Added structured schema definitions for `trip_assistant` and `attraction_explain`
- Switched both intents to JSON-only prompt contracts, matching the existing `translation` / `live_info` pattern
- Wired structured parsing in the QA generator for both intents
- Added orchestrator metadata projection for structured fields while keeping user-facing `answer` free-form
- Kept malformed structured output on the existing fallback/degraded paths instead of leaking bad JSON to users
- Added minimal non-blocking validator checks for route-aware trip guidance and grounded attraction explanations
- Added targeted QA tests for valid and malformed structured output for both intents
- Verified the QA suite passes after the change

Key files:
- `src/yoyo/modules/qa/schemas.py`
- `src/yoyo/modules/qa/prompts.py`
- `src/yoyo/modules/qa/generator.py`
- `src/yoyo/modules/qa/orchestrator.py`
- `src/yoyo/modules/qa/validators.py`
- `tests/test_qa.py`

Behavior now in place:
- `trip_assistant` can request and validate a JSON object with `answer`, `status`, `reason`, `route_focus`, `references_current_stop`, `references_next_stop`
- `attraction_explain` can request and validate a JSON object with `answer`, `status`, `reason`, `grounding`, `includes_history`, `includes_tips`
- if structured parsing fails, the system falls back to the existing route-aware / grounded degraded path instead of returning malformed model output

Verification completed:
- `tests/test_qa.py` -> **14 passed**

### 2.13 Completed itinerary edit protection
The current session also closed the next manual route-edit boundary item.

Completed in this work item:
- `POST /api/v1/planning/itineraries/{itinerary_id}/edits` now rejects edits when the itinerary is already marked `completed`
- the same route-edit entry now also rejects edits when runtime state shows there is no editable suffix left, even if the itinerary record has not yet been explicitly finished
- added a regression test proving that after the final stop is arrived + completed, further route edits are rejected with a clear 400 response

Key files:
- `src/yoyo/modules/planner/service.py`
- `tests/test_planner_edits.py`

Behavior now in place:
- if `current_stop_index >= len(stops)`, the route is treated as fully completed/frozen for manual editing
- completed itineraries no longer create new itinerary versions through the route-edit API

### 2.14 add_stop editable-suffix protection
The current session also tightened the remaining `add_stop` boundary for active trips.

Completed in this work item:
- `add_stop` now appends into the editable suffix rather than allowing reordering to disturb the completed route prefix
- route optimization and route engine application now preserve the frozen prefix and only reorder the editable portion when `add_stop` / `optimize_route` are used during an active trip
- added a regression test proving the current stop and completed prefix remain stable after adding a stop mid-trip

Key files:
- `src/yoyo/modules/planner/service.py`
- `tests/test_planner_edits.py`

Behavior now in place:
- for active trips, `stops[:editable_from_stop_index]` stays fixed during `add_stop`
- newly added stops are constrained to the editable portion of the route, with first-phase behavior still defaulting to append-to-tail semantics before suffix-only optimization

### 2.15 Public route-edit schema alignment
The current session also aligned the public route-edit request contract with the operations that are actually supported today.

Completed in this work item:
- tightened `RouteEditRequest` so each operation rejects unexpected operation-specific fields instead of silently accepting mixed payloads
- clarified the fullstack API contract so stable first-phase frontend operations are `replace_stop`, `remove_stop`, `reorder_stops`, `shorten_route`, and `add_stop`
- kept `optimize_route` as backend-supported but documented it as non-primary / not the recommended first-phase frontend control until product semantics are finalized more explicitly
- added a test proving `optimize_route` rejects unrelated fields such as `add_stop_name`

Key files:
- `src/yoyo/modules/planner/schemas.py`
- `docs/api-contracts-fullstack.md`
- `tests/test_planner_edits.py`

Behavior now in place:
- mixed route-edit payloads fail at request validation time instead of being loosely accepted
- the public contract now better matches current product guidance about which operations frontend should treat as stable versus provisional

### 2.16 Version-switch session/map/QA consistency tightening
The current session then completed the remaining version-switch consistency work.

Completed in this work item:
- active-session version switch now clears stale playback and guide-refresh context that may still point at the old route version
- current_position and trip lifecycle fields are left intact, while route-bound transient fields are reset conservatively
- `last_played_stop_id` is now also cleared when the current stop changes, not only when the old stop id disappears from the new route
- QA session-context loading now reuses `session current` instead of maintaining a separate raw current/next stop derivation path
- added fuller integration assertions for session/map state after version switch, including current/next stop, completed/editable boundaries, markers, polyline, and cleared transient context fields

Key files:
- `src/yoyo/modules/planner/service.py`
- `src/yoyo/modules/qa/orchestrator.py`
- `tests/test_a_validation_suite.py`
- `tests/test_qa.py`

Behavior now in place:
- route edit version switches no longer carry over stale `last_played_stop_index`, `last_playback_action`, `last_playback_updated_at`, `stop_segment_cursor_by_stop_id`, `played_segment_indices_by_stop_id`, `last_refresh_action`, or `last_refresh_at`
- active session context is closer to a single reliable source of truth before session/map/QA consumers read the new version
- QA now follows the same `current_stop` / `next_stop` / `playback_state` route context as `session current`, including terminal-state handling
- map payload assertions now verify that version-switch results propagate consistently to markers, polyline, navigation summary, and top-level current/next stop fields

Verification completed:
- `tests/test_a_validation_suite.py` + `tests/test_qa.py` -> **28 passed**

### 2.17 Guide structured-output validation
The current session then completed the next runtime Guide hardening step.

Completed in this work item:
- added internal structured schema for the Guide LLM bundle
- Guide generator now validates parsed JSON against the Guide bundle schema instead of only doing weak JSON parsing
- guide generation job now only passes validated LLM bundle output into `build_guide_bundle`, otherwise it falls back to the existing SQL/profile builder path while preserving generation metadata
- added focused runtime tests for valid and malformed Guide bundle output

Key files:
- `src/yoyo/modules/guide/schemas.py`
- `src/yoyo/modules/guide/generator.py`
- `src/yoyo/jobs/tasks/guide_generation.py`
- `tests/test_guide_job_runtime.py`

Behavior now in place:
- Guide runtime can now distinguish between parseable-but-invalid LLM output and validated structured bundle output
- malformed Guide bundle output no longer flows directly into the builder merge path as trusted LLM content
- the existing builder fallback remains the primary degraded path, so guide jobs can still succeed with stable bundle structure when LLM structured validation fails
- generation metadata now records whether the Guide bundle passed structured validation

Verification completed:
- `tests/test_guide_job_runtime.py` -> **2 passed**

### 2.18 Malformed-output and degraded-wording hardening
The current session then completed the next cross-runtime output-hardening step.

Completed in this work item:
- added a shared lightweight sanitizer for user-visible LLM text
- QA structured answers now sanitize wrapper/fence noise before they are accepted as valid output
- Guide bundle merge now sanitizes intro/outro/card/stop-level text fields before using LLM values
- Guide JSON extraction no longer uses the high-risk first/last-brace rescue path and instead only falls back to fenced-object extraction
- QA degraded/unavailable/redirect wording was rewritten to sound more productized and less like internal system state
- Guide default intro/outro/narration/tip fallback wording was also tightened to remove template and internal-control phrasing
- added focused malformed post-processing and degraded-wording tests for QA and Guide runtime paths

Key files:
- `src/yoyo/modules/shared_text_sanitizer.py`
- `src/yoyo/modules/qa/generator.py`
- `src/yoyo/modules/qa/formatters.py`
- `src/yoyo/modules/qa/live_info.py`
- `src/yoyo/modules/qa/orchestrator.py`
- `src/yoyo/modules/guide/generator.py`
- `src/yoyo/modules/guide/content_builder.py`
- `tests/test_qa.py`
- `tests/test_guide_job_runtime.py`

Behavior now in place:
- schema-valid but wrapper-noisy QA answers are treated as malformed and fall back instead of leaking raw noise to users
- Guide bundle text fields now strip common wrapper/fence noise before merge, and empty/dirty values naturally fall back to SQL/profile builder text
- Guide runtime no longer accepts arbitrary prose by slicing from the first `{` to the last `}`
- fenced JSON remains supported as the only relaxed JSON extraction path for structured-output recovery
- degraded/unavailable/redirect responses now avoid exposing internal state phrases like `temporarily degraded`, `current product phase`, `route/context data is refreshed`, or template-style fallback wording

Verification completed:
- `tests/test_qa.py` + `tests/test_guide_job_runtime.py` -> **22 passed**

### 2.19 Module-level failure-mode coverage
The current session then completed the next failure/degradation coverage pass.

Completed in this work item:
- added QA runtime failure tests for translation and trip_assistant when runtime generation returns provider errors
- added Guide job failure-path tests for missing itinerary version and runtime LLM error fallback
- added live_search provider config coverage for unsupported provider selection
- added knowledge-level missing-real-data coverage and RAG fallback coverage for no-positive-chunk query results
- verified the current runtime hardening stack now has module-level regression protection across QA, Guide, live_info/live_search, knowledge retrieval, and runtime-LLM post-processing

Key files:
- `tests/test_qa.py`
- `tests/test_guide_job_runtime.py`
- `tests/test_live_search.py`
- `tests/test_knowledge_retrievers.py`
- `tests/test_rag_query.py`

Behavior now protected by tests:
- missing provider config
- LLM failure
- malformed structured output
- missing real data
- upstream provider errors

Verification completed:
- `tests/test_qa.py` + `tests/test_guide_job_runtime.py` + `tests/test_live_search.py` + `tests/test_knowledge_retrievers.py` + `tests/test_rag_query.py` -> **37 passed**

### 2.20 End-to-end integration flow expansion
The current session then completed the end-to-end regression coverage around the core travel/runtime flows.

Completed in this work item:
- strengthened the main happy-path integration flow so it now covers itinerary creation, automatic guide job enqueue, guide generation job execution, asset readiness, GPS arrival, playback progression, and synchronized session/map state updates in one test
- extended the same integration flow to include a manual route edit after playback progression, and then verified version switch, session remap, map consistency, and stale context cleanup in the same chain
- added dedicated session-aware QA integration coverage for three state-change patterns: GPS arrival (`triggered`), playback completion (current stop advances), and route version switch (answer text and metadata both follow the new current stop)
- this closes all three `6.3` integration-flow items without introducing new runtime behavior changes

Key files:
- `tests/test_a_validation_suite.py`
- `tests/test_guide_playback.py`
- `tests/test_qa.py`

Behavior now protected by integration tests:
- itinerary creation automatically enqueues a guide generation job and the generated asset can be consumed by the active session
- GPS/playback state changes propagate to `session current`, `map session`, and session-aware QA consistently
- manual route edit triggers version switch, session remap, map/session consistency, and QA route-context updates in end-to-end coverage

Verification completed:
- `tests/test_a_validation_suite.py` + `tests/test_guide_playback.py` + `tests/test_qa.py` -> **35 passed**

### 2.21 Guide 4.3 product decisions and implementation
The current session also completed the immediate Guide 4.3 decisions and implementation pass.

Decisions now recorded:
- frontend does not need a visible remaining-content count for this phase; `more_content_available` remains the user-facing signal
- Guide audio should move from placeholder semantics to a real TTS/media flow
- the user plans to provide the TTS API key later
- latency matters: if one attraction can expose around 10 explainable segments, the system should avoid synchronous full-batch generation on every `cycle_content` click and instead prioritize low-latency current-stop/current-batch generation with asynchronous completion for the rest

Completed in this work item:
- `cycle_content` selection now uses user profile signals (`answer_length_preference`, `interests`, `guide_style_preference`) to rank and choose stop segments instead of taking a fixed prefix only
- Guide audio contract now moves from `not_generated` placeholder semantics to a real TTS-oriented shape with provider/model/voice settings and per-segment audio status/url fields
- `cycle_content` now returns `audio_segments` for the selected batch and uses real TTS calls when an API key is configured, while staying low-latency by generating only the current batch on demand
- when no TTS API key is configured, audio is marked `unavailable` explicitly instead of implying a future placeholder generation state

Key files:
- `src/yoyo/core/config.py`
- `src/yoyo/modules/guide/content_builder.py`
- `src/yoyo/modules/guide/asset_service.py`
- `src/yoyo/modules/guide/schemas.py`
- `src/yoyo/modules/guide/tts.py`
- `src/yoyo/jobs/tasks/guide_generation.py`
- `tests/test_guide_content_cycle.py`
- `tests/test_guide_job_runtime.py`
- `tests/test_guide_playback.py`

Behavior now in place:
- content rotation is more personalized while keeping the current single-action `cycle_content` UX
- frontend still only needs `more_content_available`, not a visible remaining counter
- audio generation is now modeled as real batch-level TTS work rather than a frozen placeholder, with latency-aware on-demand generation for the currently returned batch

Verification completed:
- `tests/test_guide_content_cycle.py` + `tests/test_guide_job_runtime.py` + `tests/test_guide_playback.py` -> **11 passed**

### 2.22 QA RAG productionization semantics pass
The current session then completed the code/test semantics pass for QA RAG productionization.

Completed in this work item:
- strengthened RAG backend readiness semantics so embedding-key absence is treated as a backend misconfiguration rather than leaving `backend_ready` overly optimistic
- aligned index/query result payloads around clearer `availability`, `status`, and `reason` semantics
- hardened admin rebuild/index-run payloads so rebuild runs explicitly describe backend status, operation type, execution mode, and final result
- extended QA metadata so attraction/RAG answers expose top-level retrieval state (`rag_retrieval_mode`, `rag_backend_ready`, `rag_backend_reason`, `rag_query_status`, `rag_query_reason`) instead of forcing callers to inspect chunk-level internals only
- added/updated regression coverage for backend readiness, admin run payloads, RAG query fallback, knowledge no-data behavior, and QA top-level RAG metadata

Key files:
- `src/yoyo/modules/knowledge/rag_backend.py`
- `src/yoyo/modules/knowledge/rag_index_service.py`
- `src/yoyo/modules/knowledge/rag_admin_service.py`
- `src/yoyo/modules/knowledge/rag_admin_schemas.py`
- `src/yoyo/modules/knowledge/rag_retriever.py`
- `src/yoyo/modules/qa/orchestrator.py`
- `tests/test_rag_backend.py`
- `tests/test_rag_admin.py`
- `tests/test_rag_query.py`
- `tests/test_knowledge_retrievers.py`
- `tests/test_qa.py`
- `docs/api-contracts-fullstack.md`

Behavior now in place:
- configured vs degraded RAG states are easier to reason about from both admin APIs and QA metadata
- admin rebuild responses now better explain whether work was skipped, succeeded, or failed, and why
- QA answers that use RAG now carry top-level retrieval state suitable for frontend/debug consumers
- the remaining open gap is real-environment validation against a configured pgvector + embedding backend, not the scaffold semantics themselves

Verification completed:
- `tests/test_rag_backend.py` + `tests/test_rag_admin.py` + `tests/test_rag_query.py` + `tests/test_knowledge_retrievers.py` + `tests/test_qa.py` -> **36 passed**

### 2.23 RAG/TTS real-environment config checklist
The current session also added an explicit configuration checklist for the next real-environment validation step.

Completed in this work item:
- documented the exact `.env` values needed for real pgvector + embedding validation
- documented the exact `.env` values needed for real TTS validation
- recorded the minimal validation steps for both RAG and Guide audio flows
- linked the preparation checklist from README so the next pass can move directly from config to execution

Key files:
- `docs/b-stack-preparation-checklist.md`
- `README.md`

Behavioral impact:
- no runtime behavior changed in this step; it only makes the next real-environment validation pass more explicit and reproducible


Remaining follow-up after this step:
- benchmark runs still need fail-fast or invalid-marking behavior when required API keys are missing

### 2.24 Real-environment RAG and Qwen TTS validation
The current session then completed the remaining real-environment validation pass.

Completed in this work item:
- switched local PostgreSQL runtime to a pgvector-capable container image so the `vector` extension could actually be created
- fixed the PostgreSQL enum migration in `0005_add_pending_guide_sessions.py` so a fresh local upgrade can proceed without dropping enum types that are still referenced by live columns
- fixed the llama-index pgvector integration so the installed `PGVectorStore.from_params(...)` signature is used correctly in the real runtime
- completed a real rebuild/latest validation cycle with `status = succeeded` and `availability = ready`
- completed a real deep QA validation path using a real created guide session, confirming QA metadata now reports `retrieval_strategy = sql_then_rag`, `rag_backend_ready = true`, and `rag_query_status = ok`
- switched Guide TTS from the blocked ElevenLabs attempt to DashScope Qwen TTS and verified real project-level synthesis output through `src/yoyo/modules/guide/tts.py`

Key files:
- `docker-compose.yml`
- `alembic/versions/0005_add_pending_guide_sessions.py`
- `src/yoyo/modules/knowledge/rag_index_service.py`
- `src/yoyo/modules/guide/tts.py`
- `src/yoyo/core/config.py`
- `pyproject.toml`
- `README.md`
- `docs/b-stack-preparation-checklist.md`
- `docs/todo.md`

Behavior now in place:
- local development can now use a pgvector-enabled Postgres image instead of failing at extension creation time
- fresh migrations no longer fail when `guide_session_status` / `itinerary_status` enums are expanded during upgrade
- RAG rebuild/latest/admin semantics now hold in a real configured environment, not only in tests
- deep attraction QA requests can now execute against a real indexed pgvector backend and return `sql_then_rag` metadata with `rag_query_status = ok`
- Guide TTS now uses DashScope Qwen TTS and can produce a real generated audio artifact from the project runtime path

---

## 3. Documentation updated in this session

Updated repeatedly through the session:
- `README.md`
- `docs/architecture.md`
- `docs/contracts.md`
- `docs/todo.md`
- `docs/todo.zh-CN.md`
- `docs/b-stack-implementation-overview.md`

These docs now reflect:
- cognitive map positioning
- Amap as route engine only
- stop comments
- share card
- QA SQL-first + RAG fallback
- RAG admin/reindex path
- Guide SQL-first multi-segment content
- unified guide content cycling

---

## 4. Tests currently passing

The following suites were run successfully at the end of this session:
- `tests/test_onboarding_flow.py`
- `tests/test_planning_entry_modes.py`
- `tests/test_session_lifecycle.py`
- `tests/test_planner_edits.py`
- `tests/test_map_gps.py`
- `tests/test_comments.py`
- `tests/test_share_card.py`
- `tests/test_a_validation_suite.py`
- `tests/test_amap_route_engine.py`
- `tests/test_qa.py`
- `tests/test_rag_backend.py`
- `tests/test_rag_indexing.py`
- `tests/test_rag_query.py`
- `tests/test_rag_admin.py`
- `tests/test_guide_asset_latest.py`
- `tests/test_guide_job_runtime.py`
- `tests/test_guide_sql_segments.py`
- `tests/test_guide_content_cycle.py`

Current result at the end of the session:
- `tests/test_guide_content_cycle.py` + `tests/test_guide_playback.py` -> **6 passed**
- `tests/test_rag_backend.py` + `tests/test_rag_query.py` -> **6 passed**
- `tests/test_runtime_openrouter.py` + `tests/test_rag_backend.py` + `tests/test_guide_content_cycle.py` + `tests/test_guide_playback.py` + `tests/test_rag_query.py` -> **13 passed**

---

## 5. Current backend shape after this session

### Guide
- SQL-first
- no Guide-side RAG in main path
- richer multi-segment SQL content
- unified `cycle_content` action for short-form audio-friendly content loops

### QA
- SQL-first + first-phase RAG fallback
- can prefer pgvector/LlamaIndex query path when configured
- can still run in degraded/mock mode before full backend config

### Map
- cognitive map
- no dependency on a real rendered map
- route polyline from route engine
- stop summaries + comment stats

### Share / social
- stop comments
- share-card read model for finished trips

### Ops / admin
- RAG index run records
- rebuild + latest status APIs
- selective/mock-friendly rebuild requests

---

## 6. Recommended next TODO

### Highest-priority remaining items
1. **Harden manual route editing with runtime-aware constraints**
   - keep route edits manual only
   - freeze completed stops
   - keep the current stop editable
   - expose editability boundaries to session/map payloads

3. **Productionize the LlamaIndex + pgvector QA RAG path**
   - complete backend-enabled retrieval in a real configured environment
   - validate embedding + pgvector end-to-end
   - harden ingestion lifecycle
   - support operational indexing / rebuild strategy

### Reasonable next concrete implementation step
If continuing from this session, the most natural next step is:

> keep tightening manual route editing semantics, especially `add_stop`, completed-itinerary protection, and version-switch consistency across session/map/frontend state.

This keeps the runtime route-edit boundary aligned before deeper QA RAG or Guide productionization work continues.

---

## 7. Important decisions to preserve

- The map is a **cognitive map**, not a real map product.
- Amap is only a **route engine**, not the rendered map.
- Guide should remain **SQL-first**, not Guide-RAG.
- QA can continue toward **SQL-first + RAG fallback**.
- The user-facing Guide refresh behavior should remain **one unified capability**, not separate “再讲一点” and “换一个” buttons.
- Route editing is currently **manual only**; QA is not the route-edit entry point in the active product path.
- When the final stop is completed, the route should be treated as fully completed/frozen with no editable stops remaining.
- QA fallback behavior has been tightened for the current phase:
  - `translation` now returns an explicit degraded response instead of phrase-map fallback when runtime generation is unavailable
  - `trip_assistant` fallback now stays route-aware and action-oriented rather than sounding like a static template
  - `live_info` now returns explicit unavailable/degraded wording and metadata when provider config or upstream requests fail
  - `attraction_explain` no longer tells users to wait for the SQL knowledge store; when grounded detail is insufficient it now returns a clearer degraded response
- Attraction/profile retrieval now distinguishes better between production-oriented and local/test fallback behavior:
  - mock seed fallback remains allowed in local/test-oriented paths
  - production-oriented behavior should no longer silently mix in mock seed records when fallback is disabled
  - profile fallback still degrades explicitly to `derived_default` rather than pretending a mock profile is real data
- The next QA productionization step should use a **minimal-impact structured-output design**:
  - keep `answer` as free-form user-facing text
  - add small internal fields such as `status`, `reason`, and intent-specific validation fields
  - start with `translation`, `live_info`, `trip_assistant`, and `attraction_explain`
  - use rule/schema validation first rather than semantic judge-style validation in the main runtime path
- The first structured-output step is now in place for QA:
  - `translation` can request and validate a JSON object with `answer`, `status`, `reason`, `mode`
  - `live_info` can request and validate a JSON object with `answer`, `status`, `reason`, `not_confirmed`, `confidence`
  - if structured parsing fails, runtime falls back to the existing degraded path instead of leaking malformed output
