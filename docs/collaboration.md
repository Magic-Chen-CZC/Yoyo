# Yoyo Collaboration Plan

This file defines the recommended two-person backend split based on the current codebase.

Read `docs/contracts.md` together before parallel development continues. That file defines the shared overlap and what must be stabilized before QA verification.

## Shared principle
Split by **runtime state** vs **intelligent content**:
- **A owner**: route, session, runtime state, map, gps
- **B owner**: guide, QA, retrieval, model evaluation, content generation

This minimizes conflicts and matches the current module layout.

## Current execution order
1. Finish the shared overlap contracts in `docs/contracts.md`
2. Freeze the Shared / coordination items in `docs/todo.md`
3. Let A and B proceed in parallel on their own tracks
4. Run broader QA verification only after the overlap contracts are stable

---

## A owner: Planner / Session / Map / GPS

### Responsibility
A owns the runtime path of the trip:
- what the route is
- what the current stop is
- where the user is
- how route edits change the active version
- what the frontend should render on map and session pages

### Main modules
- `src/yoyo/modules/questionnaire/`
- `src/yoyo/modules/planner/`
- `src/yoyo/modules/session/`
- `src/yoyo/modules/map/`
- `src/yoyo/api/v1/questionnaire.py`
- `src/yoyo/api/v1/planning.py`
- `src/yoyo/api/v1/session.py`
- `src/yoyo/api/v1/map.py`
- `src/yoyo/api/v1/gps.py`

### A immediate tasks
1. Implement real route edit flow
   - add edit request schema
   - support replace/remove/reorder/shorten route
   - create new `itinerary_version`
   - switch active version safely
2. Make session runtime state real
   - add `current_stop_index`
   - stop assuming first stop is always current
   - add next-stop progression logic
3. Add first geofence logic
   - compute distance to current stop
   - update arrived/not arrived
   - trigger stop progression rules
4. Improve map payload
   - stable marker structure
   - real current/next stop mapping
   - clearer polyline data contract
5. Tighten shared route contract
   - ensure every stop in `plan_json` has coordinates and stable fields

### A required output contract
A must keep `itinerary_version.plan_json` stable and rich enough for B to consume.
Suggested stop shape:
```json
{
  "name": "Forbidden City",
  "category": "museum",
  "latitude": 39.9163,
  "longitude": 116.3972,
  "recommended_duration_minutes": 180
}
```

### A caution
Avoid changing these contracts without updating `docs/architecture.md` and notifying B:
- `itinerary_version.plan_json`
- `guide_session.context_json`
- session current response shape

---

## B owner: Guide / QA / Retrieval / Model Eval

### Responsibility
B owns the content and model-facing path:
- what to say
- how to answer
- what guide assets exist
- how guide playback state changes
- how models are evaluated and compared
- how SQL-first attraction/profile knowledge is accessed for Guide and QA
- how short-term QA dialogue memory is managed

### Current implementation direction
- Current phase is SQL-first: attraction knowledge and user profiles should live in PostgreSQL.
- Live search remains for real-time changes only.
- RAG is deferred for now and can be introduced later if SQL-backed knowledge becomes insufficient.
- B should own the shared SQL-first knowledge access layer used by both Guide generation and QA.

### Main modules
- `src/yoyo/modules/guide/`
- `src/yoyo/modules/qa/`
- `src/yoyo/modules/poi/`
- `src/yoyo/jobs/`
- `src/yoyo/evals/`
- `src/yoyo/api/v1/guide.py`
- `src/yoyo/api/v1/qa.py`
- `evals/`

### B immediate tasks
1. Strengthen QA retrieval and live-info
   - replace placeholder sources with provider-backed source records
   - add better category-specific answer generation
   - keep QA focused on explanation / trip guidance / translation / live-info rather than route-edit execution
2. Enrich guide generation output
   - include guide script text
   - include card-like summary payloads
   - prepare output shape for future TTS and multilingual assets
3. Improve playback logic
   - connect gps trigger action to playback transitions
   - support complete/skip flows with richer metadata
4. Improve model evaluation
   - stronger rubrics
   - comparative report generation
   - per-category breakdown
   - more explicit English-only benchmark matrix
5. Prepare provider abstraction for real production use
   - avoid business logic tied to one SDK

### B required output contract
B should keep `guide_generation_job.result_json` stable enough for session/map/frontends to consume.
Suggested shape:
```json
{
  "summary": "Starter Beijing itinerary",
  "stop_count": 2,
  "stops": ["Tiananmen Square", "Forbidden City"],
  "guide_script": null,
  "card": null,
  "audio": null
}
```

---

## Shared files: coordinate carefully
These are high-conflict files. Do not both edit them casually at the same time:
- `src/yoyo/api/router.py`
- `src/yoyo/modules/shared/enums.py`
- `src/yoyo/db/models/session.py`
- `src/yoyo/db/models/itinerary.py`
- `alembic/versions/*`
- `docs/todo.md`
- `docs/architecture.md`

### Rule for migrations
Only one person should create or finalize Alembic migrations at a time.
If both sides need schema changes, collect them and merge intentionally.

### Rule for router changes
Prefer to finish module-local changes first, then wire new routes in one small final edit.

---

## Recommended near-term split

### A next sprint
- route edit endpoint and service
- itinerary version switching
- session current stop progression
- gps/geofence baseline
- map payload stabilization

### B next sprint
- retrieval-backed QA improvements
- live-info provider integration
- richer guide result output
- eval rubric/report upgrades
- English benchmark execution and analysis

---

## What B should continue now
B should continue from the current repo state with:
1. stronger evaluation rubrics and comparative reports
2. richer guide generation payloads
3. continue QA-side productionization work without reintroducing route-edit execution into the current QA path

This matches the current momentum of the project and avoids blocking A on route/runtime work.

## What must be completed before broader QA verification
- shared `itinerary_version.plan_json` contract is frozen
- shared `guide_generation_job.result_json` contract is frozen
- shared `guide_session.context_json` ownership is frozen
- `session current` payload is frozen
- GPS -> guide trigger handoff is frozen
- manual route-edit eligibility semantics are frozen
