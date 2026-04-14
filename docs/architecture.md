# Yoyo Architecture

See the Feishu revision document for the full narrative version. This repo file keeps the implementation-facing summary.

## Core decisions
- Backend-first modular monolith
- Planner module and Guide QA module are the two core business modules
- Planner is workflow/state machine/rules-first
- Guide QA is a controlled single-agent architecture
- PostgreSQL + Redis
- Async guide generation jobs
- Version-aware route and asset model

## Key concepts
- `itinerary_version`: route version boundary for planning, guide assets, and QA context
- `guide_generation_job`: async work unit for script/audio/card generation
- `asset_status`: readiness and staleness state for generated guide assets

## Current B-side knowledge architecture
- Current phase is **SQL-first**, not RAG-first.
- PostgreSQL stores attraction facts, attraction introduction fields, user profile fields, and other structured B-side knowledge.
- Live search is reserved for same-day or fast-changing travel facts such as opening hours, closures, weather, transport, or ticket changes.
- RAG remains a future evolution path only if SQL-backed knowledge becomes too limited for longer-form explanation needs.

### Shared retrieval direction
- Guide generation and QA should share one SQL-first knowledge access layer.
- They should not share one monolithic generator/orchestrator.
- Guide generation remains an async content-building path.
- QA remains an online, intent-routed answer path.

### QA memory model for the current phase
- Runtime trip state comes from `guide_session.context_json`.
- Short-term dialogue memory should come from `qa_messages` linked to the current `guide_session_id`.
- Longer-term personalization should come from a user-profile table in PostgreSQL.

### Current source-of-truth split
- SQL: attraction basics, attraction introduction, user profiles, session-aware structured context
- Live search: dynamic same-day facts
- Future RAG: long-form or document-heavy attraction knowledge if SQL fields are no longer sufficient

### Prompt field boundary for the current phase
- SQL records are the source of truth, but not every SQL field should be exposed to the model prompt.
- Attraction prompting should stay within user-facing guide fields such as intro/history/highlights/tips.
- `family_friendly_notes` is currently stored but excluded from prompt-safe projection.
- Profile prompting should stay within personalization fields such as language/interests/style/walking/pace/audience/answer-length plus `guide_style_preference`.
- Internal-only fields, operational notes, account identifiers, moderation/debug fields, and similar data should remain outside prompt construction.

### Current guide style preference buckets
- `NF`: idealist / meaning and emotional resonance
- `NT`: rational / logic and systems
- `SJ`: guardian / practical clarity and order
- `SP`: artisan / vivid, immediate, sensory experience

## State model
- `session_state`
- `navigation_state`
- `guide_state`

## Initial vertical slice
- questionnaire submission
- itinerary creation
- itinerary_version creation
- guide_generation_job enqueue and status query

---

## Shared implementation contracts
These contracts are the overlap between A and B and should be treated as frozen unless both sides agree.

### 1. `itinerary_version.plan_json`
Current agreed shape:
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

Rules:
- This is the canonical route structure.
- A owns production of this payload.
- B consumes it for QA and guide generation.
- The fields `id`, `name`, `category`, `latitude`, `longitude`, and `recommended_duration_minutes` are now part of the active contract.
- `arrival_threshold_meters` is the runtime geofence hint used by session/gps logic and is now part of the implemented stop payload.

### 2. `guide_generation_job.result_json`
Current agreed shape:
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

Rules:
- B owns production of this payload.
- A may consume it but should not mutate guide-specific meaning.
- `summary`, `stop_count`, and `stops` should remain stable.

### 3. `guide_session.context_json`
Current shared meaning:
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

Ownership:
- A-owned fields: `current_position`, `current_stop_index`, `last_arrived_stop_id`
- B-owned fields: `last_played_stop_id`, playback-related ephemeral fields

### 4. `session current` response
Current agreed shape:
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

Rules:
- A owns runtime correctness.
- B may consume this shape in QA behavior.

### 5. GPS -> guide trigger handoff
Current agreed sequence:
1. A computes arrival using geofence/distance logic.
2. A updates `guide_session.context_json` with `current_position` and `last_arrived_stop_id`.
3. If the session was `not_triggered`, arrival moves playback state to `triggered`.
4. GPS arrival does not advance `current_stop_index`.
5. B then maps later user/player actions to `playing`, `played`, or `skipped`.
6. On `complete` or `skip`, if the current stop has already arrived and a next stop exists, runtime advances `current_stop_index` and resets playback to `not_triggered`.

### 6. `planner_handoff` payload
Current agreed shape:
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

Rules:
- B owns extraction of this structured intent.
- A owns execution of route edits from this payload.

---

## Coordination rules
- Only one person should finalize Alembic migrations at a time.
- Avoid frequent simultaneous edits to `api/router.py`.
- If any shared contract changes, update `docs/contracts.md` and this file together.

---

## Runtime behaviors now implemented
- Route edits now happen through a single planning edit endpoint and always branch from the current active itinerary version.
- Each route edit creates a new `itinerary_version`, archives the old active version, and switches `itinerary.current_version_id`.
- Active `guide_session` records follow the new itinerary version automatically and remap `current_stop_index` by stop id when possible.
- Session current and map payloads are both derived from `current_stop_index`; they no longer assume the first stop is always current.
- Map session payload now exposes stable `markers`, `polyline`, and `navigation_summary` structures for frontend navigation rendering.
- GPS arrival uses haversine distance against each stop's `arrival_threshold_meters` and only triggers playback; it does not auto-advance stops.
