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
- Current phase remains **SQL-first** in implementation, and QA now has a **first-phase SQL-first + RAG fallback path** with backend readiness checks and pgvector/LlamaIndex integration hooks.
- PostgreSQL stores attraction facts, attraction introduction fields, user profile fields, and other structured B-side knowledge.
- Live search is reserved for same-day or fast-changing travel facts such as opening hours, closures, weather, transport, or ticket changes.
- Guide generation still uses SQL-grounded knowledge first and is now moving toward richer multi-segment SQL content; future Guide-side RAG support should only be considered as an optional extension, not as the primary runtime path.

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
- QA RAG fallback: supporting long-form or document-heavy attraction knowledge when SQL fields are not rich enough for deeper explanation
- Current intended RAG stack: LlamaIndex + pgvector, with final answer generation still owned by the existing QA orchestrator
- A first-phase RAG admin/readiness layer now exists so index rebuilds and latest index-run status can be observed separately from the QA request path
- The RAG rebuild path also supports selective/mock-friendly runs (for example by `poi_name`, `doc_type`, or `use_seed`) so backend behavior can be exercised before full production config is turned on.
- Future Guide RAG: keep behind a shared retrieval contract, but do not make it primary in the current phase

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

### Map product note
- The current map layer should be treated as a **cognitive map** for route understanding and stop progression, not as a full real-world base map implementation.
- The backend map payload is responsible for stop ordering, current/next stop cues, route polyline, and stop-level knowledge/comment summaries.
- Amap, in the current phase, is used only as a route-engine hook for stop ordering and polyline calculation; it is **not** the product map itself.
- Frontend rendering can later choose whether to place this payload on top of a real map provider, but the backend contract should remain useful even without one.

## First-phase product flow now being introduced
- guest quick entry (`guest session`) before full auth
- guide-role selection mapped onto `guide_style_preference`
- fixed 7-question onboarding questionnaire for profile building
- travel selection expanding toward three entry types:
  - route template
  - manual POI selection
  - AI recommendation selection
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

### 6. Manual route-edit semantics
Current agreed rule:
- Route edits are currently **manual only** through `POST /api/v1/planning/itineraries/{itinerary_id}/edits`.
- QA does not execute or hand off route edits in the active product path.
- Editability is derived from `current_stop_index`:
  - `index < current_stop_index`: completed/frozen
  - `index == current_stop_index`: current stop, still editable
  - `index > current_stop_index`: upcoming/editable

Why this boundary is used:
- GPS arrival only marks arrival and may trigger playback.
- GPS arrival does not advance `current_stop_index`.
- Playback `complete` / `skip` remains the state transition that moves route progress forward.
- Therefore the current stop can still be edited even after arrival, until playback progression advances the route.

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
- For active trips, route edits should preserve the completed route prefix; the current stop and later stops remain editable, while completed stops are fixed.
- Session current and map payloads are both derived from `current_stop_index`; they no longer assume the first stop is always current.
- Map session payload now exposes stable `markers`, `polyline`, and `navigation_summary` structures for frontend navigation rendering.
- The cognitive-map payload now also carries stop-level knowledge summaries and comment statistics so frontend stop cards do not need to make independent attraction lookups for the first-phase experience.
- GPS arrival uses haversine distance against each stop's `arrival_threshold_meters` and only triggers playback; it does not auto-advance stops.
- Guide sessions now start in a first-phase `pending` state and can be explicitly moved to `active` / `finished` through start / finish lifecycle actions.
- Initial itinerary creation and current route edits now pass through a first-phase route engine that fills `route_meta` and `polyline`; when no Amap key is configured it degrades safely to local ordering + cognitive polyline output.
- Finished trips can now be read through a dedicated share-card aggregation path that combines session lifecycle, guide card copy, map summaries, and comment statistics without mutating the guide asset contract.
- Guide content can now cycle within the current stop through SQL-backed multi-segment content (`cycle_content`) without advancing the route state.
