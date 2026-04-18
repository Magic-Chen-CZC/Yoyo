# Yoyo Shared Contracts

This file defines the overlap between A and B. These contracts should be treated as the shared boundary to finish first before broader parallel development continues.

---

## Goal
The purpose of these contracts is to let:
- A continue route/session/map/gps work safely
- B continue guide/qa/live-info/eval work safely
- the onboarding/planning flow evolve toward guest entry + profile questionnaire + multi-entry route selection without contract churn
- both sides integrate quickly and run QA verification without rework

---

## Pre-contract: guest onboarding and questionnaire flow

### Current first-phase shape
- Guest entry is handled through a lightweight guest session rather than full auth.
- The onboarding questionnaire is now a fixed versioned flow (`v1`) with 7 choice-based questions.
- The first question is a guide-role choice that is currently mapped onto `user_profiles.guide_style_preference`.
- Questionnaire submissions should carry:
  - `flow_version`
  - `role_choice`
  - `answers`
- Planner creation should now be aware of an `entry_type` such as:
  - `template`
  - `manual_poi`
  - `ai_recommendation_selected`
  - `starter_default`

### Rules
- Do not treat questionnaire submissions as arbitrary free-form payloads anymore when implementing new onboarding work.
- The onboarding role choice is currently a product-facing alias over `guide_style_preference`; if a dedicated role system is added later, update this contract and `docs/architecture.md` together.
- New planner entry types must be documented here before frontend and backend both depend on them.

---

## Contract 1: `itinerary_version.plan_json`

### Owner
- **Primary owner:** A
- **Primary consumers:** B, frontend-facing APIs

### Meaning
This is the source of truth for route structure.

### Current agreed shape
```json
{
  "summary": "Starter Beijing itinerary",
  "pace": "balanced",
  "stops": [
    {
      "id": "stop-forbidden-city",
      "name": "Forbidden City",
      "category": "museum",
      "latitude": 39.9163,
      "longitude": 116.3972,
      "recommended_duration_minutes": 180,
      "arrival_threshold_meters": 200
    }
  ]
}
```

### Rules
- A can add fields.
- A should not rename/remove the fields above without updating this file and `docs/architecture.md`.
- B may read this structure but should not reinterpret the meaning of fields ad hoc.
- Map/session/gps/QA should all treat this as the canonical route payload.
- The fields `id`, `name`, `category`, `latitude`, `longitude`, and `recommended_duration_minutes` are now part of the active contract.
- `arrival_threshold_meters` is now implemented as the per-stop geofence threshold used by runtime state.
- First-phase planner output may now also include `route_meta` and `polyline` as route-engine products for the cognitive map.

### Why it is shared
- A needs it for current/next stop, route edits, map, gps.
- B needs it for trip assistant, attraction explain context, guide generation.
- Frontend also now uses it as the backbone of the cognitive map, including stop-level knowledge, comment aggregation, and route-engine polyline output.

---

## Contract 2: `guide_generation_job.result_json`

### Owner
- **Primary owner:** B
- **Primary consumers:** A runtime views, guide playback, frontend payloads

### Meaning
This is the source of truth for generated guide content derived from an itinerary version.

### Current agreed shape
```json
{
  "summary": "Starter Beijing itinerary",
  "stop_count": 2,
  "stops": ["Tiananmen Square", "Forbidden City"],
  "guide_script": {
    "title": "Starter Beijing itinerary",
    "intro": "This route starts with Tiananmen Square and includes 2 stop(s)."
  },
  "card": {
    "headline": "Starter Beijing itinerary",
    "highlights": ["Tiananmen Square", "Forbidden City"]
  },
  "audio": {
    "status": "not_generated",
    "url": null
  }
}
```

### Rules
- B can extend this payload.
- B should preserve `summary`, `stop_count`, and `stops`.
- A should not write guide-specific fields into this object.
- Playback/asset lookup should always read the latest successful job for the active itinerary version.
- The structure above is now implemented and should be treated as the active contract.

### Why it is shared
- B uses it to represent generated guide assets.
- A/session/current endpoints may need it for guide readiness and frontend display.

---

## Contract 3: `guide_session.context_json`

### Owner
- **Shared owner**, but with field ownership rules.

### A-owned fields
- `current_position`
- `current_stop_index`
- `last_arrived_stop_id` (future)

### B-owned fields
- `last_played_stop_id` (future)
- guide/qa ephemeral context if needed

### Shared field rule
Do not add top-level keys casually. Prefer documenting new keys here first.

### Minimum current shape
```json
{
  "current_position": {
    "latitude": 39.9042,
    "longitude": 116.4074
  },
  "current_stop_index": 0,
  "last_arrived_stop_id": null,
  "last_played_stop_id": null,
  "playback_state": "not_triggered"
}
```

### Why it is shared
This is the runtime bridge between gps/session progression and guide playback / QA context.

---

## Contract 4: `session current` API payload

### Owner
- **Primary owner:** A
- **Primary consumers:** B and frontend

### Endpoint
- `GET /api/v1/session/{guide_session_id}/current`

### Required fields
```json
{
  "guide_session_id": "...",
  "itinerary_id": "...",
  "itinerary_version_id": "...",
  "status": "active",
  "playback_state": "playing",
  "current_stop_index": 0,
  "has_next_stop": true,
  "current_stop": {},
  "next_stop": {},
  "current_position": {},
  "stop_count": 2,
  "plan_summary": "..."
}
```

### Rules
- A owns the runtime correctness of this endpoint.
- B can rely on this shape for trip assistant answers and guide behavior.
- New fields can be added, but existing fields should remain stable.
- First-phase product flow now tracks `guide_session.status` as a lifecycle state: `pending` before explicit travel start, `active` during the trip, and `finished` after trip completion.
- The session/map contract now supports a cognitive-map product view rather than assuming a full real-world base map provider.

---

## Contract 5: GPS -> Guide trigger signal

### Owner
- **A produces trigger condition**
- **B consumes trigger condition for playback state**

### Shared rule
A decides whether the user has arrived at the current stop. B decides how playback state should react.

### Agreed sequence
1. A computes arrival using geofence/distance logic.
2. A updates session runtime state.
3. A emits a guide trigger condition (for now via session/runtime state; later can become explicit event).
4. GPS arrival does not advance `current_stop_index`.
5. B maps trigger -> playback state transition.
6. On `complete` or `skip`, runtime advances `current_stop_index` only if the current stop has already arrived and a next stop exists.

### Why it is shared
This is the most important runtime/content handoff in the trip flow.

---

## Contract 6: manual route-edit eligibility

### Owner
- **Primary owner:** A runtime/planning path
- **Primary consumers:** frontend route editor, session/map views

### Meaning
In the current product phase, route edits are **manual only**. QA does not execute or hand off route changes. The active route-edit entry point is:
- `POST /api/v1/planning/itineraries/{itinerary_id}/edits`

### Current rule
For an active trip, route edit eligibility is defined by runtime progress:
- stops with `index < current_stop_index` are completed/frozen
- the stop at `current_stop_index` is still editable
- stops with `index > current_stop_index` are editable

### Shared implications
- GPS arrival alone does not freeze the current stop.
- Playback `complete` / `skip` remains the progression trigger that moves the completed boundary forward.
- Reorder/replace/remove/shorten must preserve the completed prefix of the route.
- Frontend should use `session current` and map runtime payloads to determine editability.

---

## Contract 7: share-card read model

### Owner
- **Primary owner:** B aggregation layer
- **Primary consumers:** frontend share flow

### Meaning
This is the finished-trip share view. It is a read model that aggregates session lifecycle, guide card copy, route preview, and social/comment summary without mutating the underlying guide asset contract.

### Rules
- The share-card response may reuse fields from `guide_generation_job.result_json.card`, but it is a separate frontend-facing contract.
- `guide_session.status == finished` is the primary signal that a trip is shareable.
- The first-phase implementation may compute this payload on read rather than persisting a `share_cards` table.

---

## Contract 8: Schema / migration ownership

### Rule
Only one person should create/finalize Alembic migrations at a time.

### Process
- If A and B both need schema changes, collect them in one branch or sequence them intentionally.
- Shared schema files that need coordination:
  - `src/yoyo/db/models/itinerary.py`
  - `src/yoyo/db/models/session.py`
  - `src/yoyo/modules/shared/enums.py`
  - `alembic/versions/*`

---

## Contract 9: Router wiring ownership

### Rule
Avoid editing `src/yoyo/api/router.py` early and often.

### Process
- Build module-local code first.
- Wire routes in a small final change.
- If both sides need router changes in the same period, batch them.

---

## What must be finished before QA verification
Before we say QA is ready for meaningful verification, the following overlap items must be stable:

1. `itinerary_version.plan_json` stop schema is frozen
2. `guide_generation_job.result_json` baseline shape is frozen
3. `guide_session.context_json` field ownership is frozen
4. `session current` payload is frozen
5. GPS -> guide trigger handoff behavior is defined
6. manual route-edit eligibility semantics are defined

Recommended order:
1. finish these shared overlap items first
2. let A and B continue their own track implementations
3. then run broader QA verification against the stabilized contracts

Once these are stable, QA verification can focus on behavior instead of moving contracts.
