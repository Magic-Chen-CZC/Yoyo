# B Stack Implementation Overview

This document summarizes what has already been changed in the current SQL-first B implementation, how the system now works, and what should be replaced later when real PostgreSQL data becomes available.

## 1. Current phase summary

The current B implementation has been intentionally narrowed to a **SQL-first architecture**:
- PostgreSQL is the main knowledge store for B-side attraction and profile data.
- Attraction introduction content is currently expected to live in SQL fields.
- Live search is still used, but only for fast-changing travel facts such as opening hours, closures, weather, transport, or ticket changes.
- RAG is **not** part of the current implementation and is deferred to a future phase.

This phase covers:
- Guide generation
- QA
- SQL-backed retrieval
- Live-info
- Playback metadata
- Eval architecture updates

It explicitly does **not** take over A-side responsibilities such as route-edit execution, GPS arrival semantics, or current-stop progression ground truth.

---

## 2. What was changed

## 2.1 Documentation updates
The following documents were updated to reflect the SQL-first direction:
- `docs/todo.md`
- `docs/architecture.md`
- `docs/collaboration.md`
- `docs/model-evaluation.md`
- `README.md`

A new preparation document was added:
- `docs/b-stack-preparation-checklist.md`

---

## 2.2 Shared SQL-first knowledge layer
A new shared knowledge access layer was added under:
- `src/yoyo/modules/knowledge/`

Files:
- `__init__.py`
- `schemas.py`
- `seed_postgres.py`
- `sql_retriever.py`
- `profile_retriever.py`
- `attraction_retriever.py`
- `live_retriever.py`
- `hybrid_context_builder.py`

### Purpose
This layer is shared by:
- Guide generation
- QA

### Current behavior
It provides:
- attraction lookup
- profile lookup
- live-info wrapper
- unified hybrid context assembly

### Current data source
For now, this layer uses **mock PostgreSQL-style seed data** instead of a real database-backed repository.

---

## 2.3 Mock PostgreSQL seed data
The current phase includes seed-style mock data in:
- `src/yoyo/modules/knowledge/seed_postgres.py`

### Included now
- 50 mock attraction records
- 50 mock user profile records

### Attraction fields currently modeled
- `id`
- `name`
- `aliases`
- `category`
- `latitude`
- `longitude`
- `recommended_duration_minutes`
- `tags`
- `short_intro`
- `history`
- `highlights`
- `visitor_tips`
- `practical_notes`
- `family_friendly_notes`
- `photo_spot_notes`

### User profile fields currently modeled
- `user_id`
- `preferred_language`
- `interests`
- `travel_style`
- `walking_preference`
- `pace_preference`
- `audience_type`
- `answer_length_preference`

---

## 2.4 New SQL models and migration
Two new ORM models were added:
- `src/yoyo/db/models/attraction.py`
- `src/yoyo/db/models/profile.py`

Exports were updated in:
- `src/yoyo/db/models/__init__.py`

Alembic wiring was updated in:
- `alembic/env.py`

A new migration was added:
- `alembic/versions/0002_add_attractions_and_user_profiles.py`

### Why this matters
The system is no longer only pretending to be SQL-first at the service layer — it now has real schema-level placeholders for:
- attraction data
- user profile data

This is what should later be connected to real PostgreSQL content.

---

## 2.5 QA retrieval moved away from static POI-only logic
The old POI dictionary path was still present, but the logic now prefers the new knowledge layer.

Changed files:
- `src/yoyo/modules/poi/service.py`
- `src/yoyo/modules/qa/retrieval.py`

### Current behavior
The QA retrieval path now prefers:
- SQL-first attraction retrieval via the knowledge layer
- and only falls back to the old `POI_CATALOG` if needed

### Current retrieval payload is richer
The retrieval output now includes more than the old `name/summary/history/tips` structure.
It can now include:
- `id`
- `aliases`
- `category`
- `highlights`
- `source_type`
- `evidence`

---

## 2.6 QA now has short-term dialogue memory
A new helper was added:
- `src/yoyo/modules/qa/history.py`

### Current behavior
The system now uses `qa_messages` as short-term conversation memory:
- each user message can be written to `qa_messages`
- each assistant response can be written to `qa_messages`
- recent history can be loaded before generating a new answer

### Current memory model
The QA stack now follows this memory split:
- runtime trip state: `guide_session.context_json`
- short-term dialogue memory: `qa_messages`
- longer-term personalization: SQL-backed user profile data

This is the first real multi-turn step beyond single-turn QA.

---

## 2.7 QA orchestrator was upgraded
Main file:
- `src/yoyo/modules/qa/orchestrator.py`

### What changed
The QA flow now does the following:
1. loads session context
2. loads recent dialogue history
3. detects intent with dialogue-aware logic
4. writes the user turn into `qa_messages`
5. builds a hybrid SQL-first context
6. generates an answer using intent-specific formatting
7. validates the answer with intent-aware checks
8. writes the assistant turn into `qa_messages`

### Important behavior changes
- it now prefers `current_stop_index` from session context when available
- it no longer behaves like a pure single-turn stateless helper
- it now attaches richer metadata for retrieval/profile/live-info cases

---

## 2.8 Intent routing and domain guard were strengthened
Changed files:
- `src/yoyo/modules/qa/intent_router.py`
- `src/yoyo/modules/qa/domain_guard.py`

### Current intent strategy
Still rules-first, but improved.

### Now better covers
- more English phrasing
- some Chinese trigger words
- follow-up phrasing in multi-turn dialogue
- stronger planner-handoff priority

### Important note
This is **not** a full LLM intent classifier.
It is still a controlled routing system, which is consistent with the project’s backend-first design.

---

## 2.9 QA output formatting is no longer pure placeholder logic
Changed file:
- `src/yoyo/modules/qa/formatters.py`

### Current upgrades
- translation no longer returns the old guided-mode placeholder
- trip assistant answers include current/next/remaining context and pacing hints
- attraction explain answers use a more guide-like structure
- live-info answers explicitly remind users to verify same-day information
- planner handoff answers expose operation/target/constraints more clearly

---

## 2.10 planner_handoff extraction is broader now
Changed files:
- `src/yoyo/modules/qa/planner_handoff.py`
- `src/yoyo/modules/qa/schemas.py`

### Supported operation coverage now includes
- `replace_stop`
- `remove_stop`
- `reorder_stops`
- `shorten_route`
- `update_route`

### Constraints can now include
- `theme`
- `walking`
- `pace`
- `audience`
- `crowd`
- `time_budget`
- `position_hint`

### Contract note
This still preserves the existing shared top-level shape:
- `intent`
- `operation`
- `target`
- `constraints`

---

## 2.11 Guide generation is now profile-aware and SQL-grounded
New file:
- `src/yoyo/modules/guide/content_builder.py`

Changed file:
- `src/yoyo/jobs/tasks/guide_generation.py`

### Previous behavior
Guide generation used to be mostly a route summary transformer.

### Current behavior
Guide generation now uses:
- route data
- attraction SQL-style content
- user profile context

### Current output still preserves the shared top-level contract
The top-level result still includes:
- `summary`
- `stop_count`
- `stops`
- `guide_script`
- `card`
- `audio`

### But internal richness has increased
`guide_script` now includes:
- `title`
- `intro`
- `language`
- `stops[]`
- `outro`

Each stop may include:
- `stop_id`
- `stop_name`
- `narration`
- `why_it_matters`
- `visitor_tip`
- `recommended_duration_minutes`

`card` now includes:
- `headline`
- `highlights`
- `route_style`
- `practical_tips`

`audio` now includes:
- `status`
- `url`
- `language`
- `voice`
- `estimated_duration_seconds`
- `segments`

---

## 2.12 Planner -> Guide profile linkage was added
Changed file:
- `src/yoyo/modules/planner/service.py`

### What changed
`planner_input_json` now also stores:
- `user_id`

### Why this matters
Guide generation can now pull the profile using the itinerary version’s planner input, which is essential for profile-aware content building.

---

## 2.13 Playback metadata was enriched
Changed file:
- `src/yoyo/modules/guide/asset_service.py`

### Current playback metadata now tracks
- `playback_state`
- `last_playback_action`
- `last_playback_updated_at`
- `last_played_stop_id`
- `last_played_stop_index` (when safely inferable)

### Important boundary
This does **not** take ownership of A-side runtime semantics such as:
- arrival detection
- true current stop progression
- GPS interpretation

It stays within B-owned playback metadata.

---

## 2.14 Eval architecture was updated
Changed files include:
- `src/yoyo/evals/providers.py`
- `src/yoyo/evals/scoring.py`
- `src/yoyo/evals/reporting.py`
- `evals/models.yaml`
- `evals/datasets/query_templates.yaml`
- `evals/datasets/planner_handoff_queries.json`
- `evals/datasets/multilingual_queries.yaml`

### Current eval improvements
- provider registry now supports more providers cleanly
- dataset now includes planner handoff and guide-generation-oriented categories
- multilingual samples were added
- scoring now reflects SQL grounding, planner extraction, profile-aware guide generation, and multi-turn continuity directions
- reporting now includes language breakdown in addition to category breakdown

---

## 3. What the system now does differently

## QA path
Current QA path now behaves like this:
1. read session context
2. read recent dialogue turns
3. detect intent
4. build SQL-first hybrid context
5. answer using attraction facts/profile/live-info as needed
6. write dialogue turns back into memory

This is no longer just a thin single-turn endpoint.

## Guide generation path
Current guide generation path now behaves like this:
1. read itinerary version
2. read user profile
3. read SQL-backed attraction content
4. build route-aware guide content bundle
5. persist the enriched guide asset result

---

## 4. What is still mock / transitional

The following are still transitional and should later be replaced with real data:

### 1) mock attraction data
Currently from:
- `src/yoyo/modules/knowledge/seed_postgres.py`

### 2) mock user profile data
Currently from:
- `src/yoyo/modules/knowledge/seed_postgres.py`

### 3) attraction retrieval source
Currently goes through mock SQL-style retrieval rather than real PostgreSQL queries

### 4) no current RAG pipeline
The system is intentionally SQL-first in this phase

### 5) tests were intentionally deferred
This implementation phase focused on architecture and core flows, not full regression coverage

---

## 5. What should be replaced when real PostgreSQL data is ready

When real data becomes available, the main replacement points are:

## 5.1 replace the mock attraction seed source
Current placeholder:
- `src/yoyo/modules/knowledge/seed_postgres.py`
- `src/yoyo/modules/knowledge/attraction_retriever.py`

Future target:
- actual repository/query implementation backed by the `attractions` table

## 5.2 replace the mock profile seed source
Current placeholder:
- `src/yoyo/modules/knowledge/seed_postgres.py`
- `src/yoyo/modules/knowledge/profile_retriever.py`

Future target:
- actual repository/query implementation backed by the `user_profiles` table

## 5.3 define safe field exposure rules
Before real prompts use real profile or attraction data, confirm:
- which fields are safe to expose to the model
- which fields are for internal logic only

### Current recommendation
Use a prompt-safe projection layer once real PostgreSQL data is connected.
That means:
- query the full database record if needed for application logic
- but only send the approved subset into prompt construction

Suggested prompt-safe attraction subset:
- `name`
- `aliases`
- `category`
- `recommended_duration_minutes`
- `short_intro`
- `history`
- `highlights`
- `visitor_tips`
- `practical_notes`
- `photo_spot_notes`

Current exclusion note:
- `family_friendly_notes` remains stored in SQL but is excluded from prompt-safe projection in the current phase.

Suggested prompt-safe profile subset:
- `preferred_language`
- `interests`
- `travel_style`
- `walking_preference`
- `pace_preference`
- `audience_type`
- `answer_length_preference`
- `guide_style_preference`

Current style buckets for `guide_style_preference`:
- `NF`: idealist / meaning- and emotion-oriented
- `NT`: rational / logic- and system-oriented
- `SJ`: guardian / practical and orderly
- `SP`: artisan / vivid and experience-oriented

Do not directly pass raw rows containing internal-only fields into prompt construction.

## 5.4 optionally add real FAQ / operational tables
If available later, add SQL tables for:
- attraction FAQ
- attraction policy notes
- guide style config
- user preference overrides

---

## 6. What is intentionally deferred

These areas are intentionally not finished in this phase:
- full regression test suite updates
- formal integration test coverage
- full real PostgreSQL repository layer
- RAG / vector retrieval
- LLM-based intent classification
- A-side runtime semantics such as real stop progression or route edit execution

---

## 7. Recommended next steps

Recommended next steps from here:
1. connect the knowledge layer to real PostgreSQL queries
2. confirm production-safe field exposure rules
3. decide whether QA should keep only recent dialogue turns or also add conversation summaries later
4. add focused tests for:
   - multi-turn QA
   - planner_handoff extraction
   - profile-aware guide generation
   - playback metadata
   - eval datasets and scoring behavior
5. only after SQL-backed knowledge becomes insufficient, discuss whether to reintroduce RAG

---

## 8. Quick file map

### Shared SQL-first knowledge layer
- `src/yoyo/modules/knowledge/__init__.py`
- `src/yoyo/modules/knowledge/schemas.py`
- `src/yoyo/modules/knowledge/seed_postgres.py`
- `src/yoyo/modules/knowledge/sql_retriever.py`
- `src/yoyo/modules/knowledge/profile_retriever.py`
- `src/yoyo/modules/knowledge/attraction_retriever.py`
- `src/yoyo/modules/knowledge/live_retriever.py`
- `src/yoyo/modules/knowledge/hybrid_context_builder.py`

### QA
- `src/yoyo/modules/qa/history.py`
- `src/yoyo/modules/qa/orchestrator.py`
- `src/yoyo/modules/qa/intent_router.py`
- `src/yoyo/modules/qa/domain_guard.py`
- `src/yoyo/modules/qa/formatters.py`
- `src/yoyo/modules/qa/planner_handoff.py`
- `src/yoyo/modules/qa/validators.py`
- `src/yoyo/modules/qa/retrieval.py`

### Guide
- `src/yoyo/modules/guide/content_builder.py`
- `src/yoyo/jobs/tasks/guide_generation.py`
- `src/yoyo/modules/guide/asset_service.py`

### DB / migration
- `src/yoyo/db/models/attraction.py`
- `src/yoyo/db/models/profile.py`
- `alembic/versions/0002_add_attractions_and_user_profiles.py`

### Eval
- `src/yoyo/evals/providers.py`
- `src/yoyo/evals/scoring.py`
- `src/yoyo/evals/reporting.py`
- `evals/models.yaml`
- `evals/datasets/query_templates.yaml`
- `evals/datasets/planner_handoff_queries.json`
- `evals/datasets/multilingual_queries.yaml`
