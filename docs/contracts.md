# Yoyo Shared Contracts

This file defines the overlap between A and B. These contracts should be treated as the shared boundary to finish first before broader parallel development continues.

---

## Goal
The purpose of these contracts is to let:
- A continue route/session/map/gps work safely
- B continue guide/qa/live-info/eval work safely
- both sides integrate quickly and run QA verification without rework

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

### Why it is shared
- A needs it for current/next stop, route edits, map, gps.
- B needs it for trip assistant, attraction explain context, guide generation.

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

## Contract 6: `planner_handoff` intent payload

### Owner
- **B owns intent extraction**
- **A owns execution of route edits**

### Meaning
When QA identifies that a user request is really a route-edit request, B should return a structured intent payload that A can execute.

### Current agreed shape
```json
{
  "intent": "planner_handoff",
  "operation": "replace_stop",
  "target": "Jingshan Park",
  "constraints": {
    "theme": "scenic",
    "walking": "lighter"
  }
}
```

This structure is now implemented in the QA path and should be treated as the active contract for A to consume.

### Rules
- B should standardize operation names.
- A should consume only agreed operation names.
- Any new operation must be documented here before implementation on both sides.

---

## Contract 7: Schema / migration ownership

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

## Contract 8: Router wiring ownership

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
6. `planner_handoff` structured payload shape is defined

Recommended order:
1. finish these shared overlap items first
2. let A and B continue their own track implementations
3. then run broader QA verification against the stabilized contracts

Once these are stable, QA verification can focus on behavior instead of moving contracts.
