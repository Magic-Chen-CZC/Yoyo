# Yoyo Fullstack API Contracts

This document is the working frontend/backend integration contract for the current first-phase product.

It covers the current `/api/v1` surface, the common response envelope, major request/response shapes, key runtime semantics, and the intended integration order for frontend development.

## Current product boundary
- Route changes are currently **manual only**.
- QA does **not** execute or hand off route changes in the current product path.
- The only route-edit entry point is:
  - `POST /api/v1/planning/itineraries/{itinerary_id}/edits`
- Route edit rule for active trips:
  - completed stops are frozen
  - the current stop is still editable
  - future stops are editable
- Frontend should use `session current` and `map session` payloads as the route runtime source of truth.

---

## 1. Common response envelope

All successful API responses currently use:

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

Implementation source:
- `src/yoyo/api/responses.py`

Notes:
- `message` may be `success`, `created`, or `ok` depending on endpoint.
- Error responses follow FastAPI default style for raised exceptions, for example:

```json
{
  "detail": "itinerary not found"
}
```

Common failure behavior in current phase:
- `400`: invalid request payload or invalid edit operation
- `404`: resource not found / content unavailable

---

## 2. Health

### `GET /api/v1/health`
Purpose:
- Basic service liveness check.

Success response:
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "status": "ok"
  }
}
```

---

## 3. Guest onboarding

### `POST /api/v1/guest/sessions`
Purpose:
- Create a first-phase guest session before full auth exists.

Request body:
- none

Success response data shape:
```json
{
  "guest_user_id": "guest_xxx",
  "anonymous_token": "token_xxx",
  "status": "active"
}
```

Schema source:
- `src/yoyo/modules/guest/schemas.py` → `GuestSessionCreateResponse`

Frontend usage:
- Call at app entry when user starts without a formal account.
- Persist `guest_user_id` for questionnaire and itinerary creation.

---

## 4. Questionnaire

### `GET /api/v1/questionnaire/flows/current`
Purpose:
- Fetch the fixed first-phase questionnaire flow.

Success response data shape:
```json
{
  "version": "v1",
  "question_count": 7,
  "questions": [
    {
      "id": "guide_role",
      "type": "single_select",
      "title": "Choose your guide role",
      "options": [
        {"value": "balanced_storyteller", "label": "Balanced storyteller"}
      ]
    }
  ]
}
```

Schema source:
- `src/yoyo/modules/questionnaire/schemas.py` → `QuestionnaireFlowRead`
- `src/yoyo/modules/questionnaire/flow.py`

Notes:
- Current version is fixed to `v1`.
- `guide_role` is still stored as a product-facing choice and mapped to `guide_style_preference` internally.

### `POST /api/v1/questionnaire/submissions`
Purpose:
- Submit the fixed questionnaire answers and create/update the first-phase profile payload.

Request body shape:
```json
{
  "user_id": "guest_xxx",
  "source": "questionnaire",
  "role_choice": "balanced_storyteller",
  "flow_version": "v1",
  "answers": {
    "preferred_language": "en",
    "interests": ["history", "architecture"],
    "travel_style": "balanced",
    "walking_preference": "moderate",
    "audience_type": "general",
    "answer_length_preference": "short"
  }
}
```

Important validation rule:
- The backend normalizes `guide_role` from `role_choice` and requires all 7 questions.

Success response data shape:
```json
{
  "id": "submission_xxx",
  "user_id": "guest_xxx",
  "source": "questionnaire",
  "status": "submitted",
  "payload": {
    "flow_version": "v1",
    "role_choice": "balanced_storyteller",
    "answers": {}
  }
}
```

Schema source:
- `src/yoyo/modules/questionnaire/schemas.py` → `QuestionnaireSubmissionCreate`, `QuestionnaireSubmissionRead`

Frontend usage:
- Submit after onboarding choices are complete.
- Use the returned submission id when creating an itinerary if needed.

---

## 5. Planning

### `GET /api/v1/planning/templates`
Purpose:
- Fetch first-phase route templates.

Success response data shape:
```json
[
  {
    "id": "classic-central-beijing",
    "title": "Classic Central Beijing",
    "summary": "A classic first-day route through Beijing landmarks.",
    "pace": "balanced",
    "tags": ["history", "landmark", "first_visit"],
    "stop_ids": ["stop-tiananmen-square", "stop-forbidden-city"]
  }
]
```

Source:
- `src/yoyo/modules/planner/template_repository.py`

### `POST /api/v1/planning/recommendations`
Purpose:
- Generate first-phase route recommendations from user preferences.

Request body:
```json
{
  "user_id": "guest_xxx",
  "preferences": {
    "travel_style": "relaxed",
    "interests": ["views", "photography"]
  }
}
```

Success response data shape:
```json
[
  {
    "recommendation_id": "rec_xxx",
    "title": "Relaxed View Route",
    "summary": "A lighter route with open spaces and city views.",
    "entry_type": "ai_recommendation_selected",
    "template_id": null,
    "selected_poi_ids": ["stop-tiananmen-square", "stop-jingshan-park"],
    "tags": ["views", "relaxed"]
  }
]
```

Schema source:
- `src/yoyo/modules/planner/recommendation_schemas.py`

### `POST /api/v1/planning/itineraries`
Purpose:
- Create a new itinerary and its initial active itinerary version.

Request body shape:
```json
{
  "user_id": "guest_xxx",
  "city_code": "beijing",
  "title": "My Beijing trip",
  "questionnaire_submission_id": "submission_xxx",
  "entry_type": "template",
  "template_id": "classic-central-beijing",
  "selected_poi_ids": [],
  "preferences": {
    "preferred_poi_count": 2
  }
}
```

`entry_type` values currently supported:
- `template`
- `manual_poi`
- `ai_recommendation_selected`
- `starter_default`

Validation rules:
- `template` requires `template_id`
- `manual_poi` requires `selected_poi_ids`

Success response data shape:
```json
{
  "id": "itinerary_xxx",
  "user_id": "guest_xxx",
  "city_code": "beijing",
  "title": "My Beijing trip",
  "status": "active",
  "current_version_id": "version_xxx",
  "version": {
    "id": "version_xxx",
    "version_no": 1,
    "status": "active",
    "planner_input": {},
    "plan": {
      "summary": "Starter Beijing itinerary",
      "pace": "balanced",
      "stops": [
        {
          "id": "stop-tiananmen-square",
          "name": "Tiananmen Square",
          "category": "landmark",
          "latitude": 39.905,
          "longitude": 116.3976,
          "recommended_duration_minutes": 90,
          "arrival_threshold_meters": 200
        }
      ],
      "route_meta": {
        "optimization_status": "optimized",
        "routing_provider": null,
        "waypoint_order_source": "starter_default"
      },
      "polyline": []
    }
  }
}
```

Schema source:
- `src/yoyo/modules/planner/schemas.py` → `CreateItineraryRequest`, `ItineraryRead`, `ItineraryVersionRead`

Notes:
- The backend creates a guide generation job automatically after itinerary creation.
- `plan.stops` is the canonical route structure for frontend route rendering.

### `GET /api/v1/planning/itineraries/{itinerary_id}`
Purpose:
- Read the current active itinerary and active version.

Response data shape:
- Same as `POST /planning/itineraries` success data.

### `GET /api/v1/planning/itineraries/{itinerary_id}/versions`
Purpose:
- Read current and previous itinerary versions.

Success response data shape:
```json
[
  {
    "id": "version_2",
    "version_no": 2,
    "status": "active",
    "planner_input": {},
    "plan": {}
  },
  {
    "id": "version_1",
    "version_no": 1,
    "status": "archived",
    "planner_input": {},
    "plan": {}
  }
]
```

Frontend usage:
- Version history / debug / future rollback visualization.
- Not required for the core first-phase golden path UI.

### `POST /api/v1/planning/itineraries/{itinerary_id}/edits`
Purpose:
- Manually edit the active route by creating a new itinerary version.

This is the **only** current route-edit entry point.

Request body schema:
```json
{
  "operation": "replace_stop",
  "target_stop_id": "stop-forbidden-city",
  "target_stop_name": null,
  "replacement_stop_id": null,
  "replacement_stop_name": "Jingshan Park",
  "add_stop_id": null,
  "add_stop_name": null,
  "ordered_stop_ids": [],
  "target_stop_count": null,
  "created_by": "planner_edit_api"
}
```

Current `operation` values:
- `replace_stop`
- `remove_stop`
- `reorder_stops`
- `shorten_route`
- `add_stop`
- `optimize_route`

Current first-phase support status:
- `replace_stop`, `remove_stop`, `reorder_stops`, `shorten_route`, `add_stop` are the primary frontend-facing manual edit operations
- `optimize_route` remains a backend-supported operation, but it is not the recommended first-phase frontend control until product semantics are finalized more explicitly

Operation-specific request requirements:
- `replace_stop`
  - needs `target_stop_id` or `target_stop_name`
  - needs `replacement_stop_id` or `replacement_stop_name`
  - should not send `add_stop_*`, `ordered_stop_ids`, or `target_stop_count`
- `remove_stop`
  - needs `target_stop_id` or `target_stop_name`
  - should not send replacement/add/reorder/shorten fields
- `reorder_stops`
  - needs `ordered_stop_ids`
  - should not send target/replacement/add/shorten fields
- `shorten_route`
  - needs `target_stop_count`
  - should not send target/replacement/add/reorder fields
- `add_stop`
  - needs `add_stop_id` or `add_stop_name`
  - should not send target/replacement/reorder/shorten fields
- `optimize_route`
  - should send no operation-specific fields beyond `operation` and optional `created_by`

### Manual route edit semantics for active trips
Frontend must assume the following product rule:
- completed stops are frozen
- the current stop is editable
- future stops are editable

Practical UI implications:
- disable edit actions on completed stops
- allow edit actions on the current stop and later stops
- treat `add_stop` as an editable-suffix operation; in the current first phase it should behave like append-to-tail rather than a free insert into the completed prefix
- prefer exposing `replace_stop`, `remove_stop`, `reorder_stops`, `shorten_route`, and `add_stop` as the stable first-phase UI operations
- keep `optimize_route` behind an internal or clearly experimental UI path unless product semantics are explicitly approved
- after every successful edit, refresh:
  - `GET /api/v1/session/{guide_session_id}/current`
  - `GET /api/v1/map/session/{guide_session_id}`
  - optionally `GET /api/v1/guide/asset/{guide_session_id}` after regeneration becomes relevant

Current backend behavior after a successful edit:
- creates a new `itinerary_version`
- archives the previous active version
- switches `itinerary.current_version_id`
- remaps active guide sessions to the new version
- re-enqueues guide generation

Success response data shape:
- same `ItineraryRead` envelope as create/get itinerary

Common 400 cases:
- invalid operation payload
- target stop not found in route
- replacement stop already exists in route
- route would become invalid
- edit conflicts with frozen/completed portion of the route
- reorder payload does not preserve required route structure

Common 404 cases:
- itinerary not found

---

## 6. Session lifecycle and runtime state

### `POST /api/v1/session/guide`
Purpose:
- Create a guide session bound to an itinerary version.

Request body:
```json
{
  "itinerary_id": "itinerary_xxx",
  "itinerary_version_id": "version_xxx",
  "context": {
    "current_stop_index": 0
  }
}
```

Success response data shape:
```json
{
  "id": "guide_session_xxx",
  "itinerary_id": "itinerary_xxx",
  "itinerary_version_id": "version_xxx",
  "status": "pending",
  "context": {
    "current_stop_index": 0,
    "current_position": null,
    "last_arrived_stop_id": null,
    "last_played_stop_id": null,
    "playback_state": "not_triggered",
    "trip_state": "pending"
  }
}
```

Schema source:
- `src/yoyo/modules/session/schemas.py` → `CreateGuideSessionRequest`, `GuideSessionRead`

### `GET /api/v1/session/guide/{guide_session_id}`
Purpose:
- Read the raw guide session record and runtime context.

Use cases:
- debug / internal tooling / finer session-state inspection
- not the main frontend route runtime view

### `POST /api/v1/session/guide/{guide_session_id}/start`
Purpose:
- Explicitly start the trip.

Success response data shape:
```json
{
  "guide_session_id": "guide_session_xxx",
  "status": "active",
  "playback_state": "not_triggered"
}
```

### `POST /api/v1/session/guide/{guide_session_id}/finish`
Purpose:
- Explicitly finish the trip.

Success response data shape:
```json
{
  "guide_session_id": "guide_session_xxx",
  "status": "finished",
  "playback_state": "played"
}
```

### `GET /api/v1/session/{guide_session_id}/current`
Purpose:
- Main runtime source of truth for frontend trip state.

Current stable response shape:
```json
{
  "guide_session_id": "guide_session_xxx",
  "itinerary_id": "itinerary_xxx",
  "itinerary_version_id": "version_xxx",
  "status": "active",
  "playback_state": "playing",
  "current_stop_index": 0,
  "has_next_stop": true,
  "current_stop": {},
  "next_stop": {},
  "current_position": {
    "latitude": 39.905,
    "longitude": 116.3976
  },
  "stop_count": 2,
  "plan_summary": "Starter Beijing itinerary"
}
```

Current route-edit boundary semantics for frontend:
- `current_stop_index` is the route progress boundary
- stops before it should be treated as completed/frozen
- the stop at `current_stop_index` is still editable
- later stops are editable

Planned contract extension for frontend route editing:
- `completed_stop_count`
- `editable_from_stop_index`
- `frozen_stop_ids`
- `editable_stop_ids`

Until those fields land in code, frontend should derive editability from `current_stop_index`.

---

## 7. GPS

### `POST /api/v1/gps/update/{guide_session_id}`
Purpose:
- Update current position and determine whether the user has arrived at the current stop.

Request body:
```json
{
  "latitude": 39.905,
  "longitude": 116.3976
}
```

Success response data shape:
```json
{
  "guide_session_id": "guide_session_xxx",
  "current_position": {
    "latitude": 39.905,
    "longitude": 116.3976
  },
  "current_stop_index": 0,
  "current_stop": {
    "id": "stop-tiananmen-square"
  },
  "distance_to_current_stop_meters": 0,
  "arrival_threshold_meters": 200,
  "arrived": true
}
```

Important semantics:
- GPS arrival sets arrival state for the current stop.
- GPS arrival may move playback state to `triggered`.
- GPS arrival does **not** advance `current_stop_index`.
- Therefore GPS arrival alone does **not** freeze the current stop for editing.
- On the final stop, playback `complete` / `skip` should move the route into a fully completed state with no editable stops remaining.

Frontend implication:
- Do not mark the current stop as completed just because `arrived=true`.
- Completion still depends on playback completion/skip progression.

---

## 8. Guide and playback

### `POST /api/v1/guide/jobs`
Purpose:
- Manually create a guide generation job for an itinerary version.

Request body:
```json
{
  "itinerary_version_id": "version_xxx",
  "payload": {}
}
```

Success response data shape:
```json
{
  "id": "job_xxx",
  "itinerary_version_id": "version_xxx",
  "job_type": "guide_bundle",
  "status": "queued",
  "asset_status": "pending",
  "payload": {},
  "result": null,
  "error_code": null,
  "error_message": null
}
```

### `GET /api/v1/guide/jobs/{guide_generation_job_id}`
Purpose:
- Read the state of a guide generation job.

### `GET /api/v1/guide/asset/{guide_session_id}`
Purpose:
- Read the latest active guide asset for the current session version.

Success response data shape:
```json
{
  "guide_session_id": "guide_session_xxx",
  "playback_state": "not_triggered",
  "asset_status": "ready",
  "summary": "Starter Beijing itinerary",
  "stops": ["Tiananmen Square", "Forbidden City"],
  "result": {
    "summary": "Starter Beijing itinerary",
    "stop_count": 2,
    "stops": ["Tiananmen Square", "Forbidden City"],
    "guide_script": {},
    "card": {},
    "audio": {
      "status": "not_generated",
      "url": null
    }
  }
}
```

### `POST /api/v1/guide/playback/{guide_session_id}`
Purpose:
- Update playback state transitions.

Request body:
```json
{
  "action": "play"
}
```

Common action values in current phase:
- `trigger`
- `play`
- `complete`
- `skip`

Success response data shape:
```json
{
  "guide_session_id": "guide_session_xxx",
  "playback_state": "playing"
}
```

Important semantics:
- `complete` / `skip` may advance `current_stop_index` if the current stop has already arrived and a next stop exists.
- That is the main runtime progression used to decide whether a stop becomes completed/frozen.

### `POST /api/v1/guide/content/{guide_session_id}`
Purpose:
- Cycle guide content within the current stop without advancing route state.

Request body:
```json
{
  "action": "cycle_content"
}
```

Success response data shape:
```json
{
  "guide_session_id": "guide_session_xxx",
  "stop_id": "stop-tiananmen-square",
  "stop_name": "Tiananmen Square",
  "action": "cycle_content",
  "segments": ["segment 1", "segment 2"],
  "segment_count": 10,
  "more_content_available": true,
  "guide_style": "SJ"
}
```

Important semantics:
- This endpoint does **not** advance route state.
- Finished sessions reject content cycling.

---

## 9. Cognitive map

### `GET /api/v1/map/session/{guide_session_id}`
Purpose:
- Fetch the frontend-facing cognitive map payload for the current session.

Current response data shape:
```json
{
  "guide_session_id": "guide_session_xxx",
  "markers": [
    {
      "id": "stop-tiananmen-square",
      "name": "Tiananmen Square",
      "category": "landmark",
      "latitude": 39.905,
      "longitude": 116.3976,
      "order": 0,
      "is_current": true,
      "is_next": false,
      "short_intro": "...",
      "highlights": ["..."],
      "visitor_tip": "...",
      "source_type": "sql",
      "comment_count": 2,
      "latest_comment_preview": "..."
    }
  ],
  "polyline": [
    {
      "stop_id": "stop-tiananmen-square",
      "order": 0,
      "latitude": 39.905,
      "longitude": 116.3976
    }
  ],
  "navigation_summary": {
    "current_stop_index": 0,
    "stop_count": 2,
    "remaining_stop_count": 1,
    "has_next_stop": true
  },
  "current_position": {
    "latitude": 39.905,
    "longitude": 116.3976
  },
  "current_stop": {},
  "next_stop": {}
}
```

Current frontend semantics:
- Use `markers[].order` for route ordering.
- Use `is_current` / `is_next` for current navigation emphasis.
- Use `navigation_summary.current_stop_index` as the current route progress boundary.
- Combine map payload with session current when rendering route edit UI.

Planned contract extension for route editing UI:
- `markers[].is_completed`
- `markers[].is_editable`
- `navigation_summary.completed_stop_count`
- `navigation_summary.editable_from_stop_index`

---

## 10. Comments

### `GET /api/v1/comments/stops/{stop_id}`
Purpose:
- List comments for a stop.

Success response data shape:
```json
[
  {
    "id": "comment_xxx",
    "stop_id": "stop-tiananmen-square",
    "user_id": "guest_xxx",
    "content": "Great place for photos.",
    "status": "active",
    "guide_session_id": "guide_session_xxx",
    "created_at": "2026-04-15T12:00:00+00:00"
  }
]
```

Schema source:
- `src/yoyo/modules/comments/schemas.py` → `CommentRead`

### `POST /api/v1/comments/stops/{stop_id}`
Purpose:
- Create a new comment for a stop.

Request body:
```json
{
  "user_id": "guest_xxx",
  "content": "Great place for photos.",
  "guide_session_id": "guide_session_xxx"
}
```

Success response data shape:
- `CommentRead`

Frontend usage:
- Stop detail sheet / review entry / trip memory comments.

---

## 11. Share card

### `GET /api/v1/share-card/session/{guide_session_id}`
Purpose:
- Read the frontend-facing finished-trip share payload.

Success response data shape:
```json
{
  "guide_session_id": "guide_session_xxx",
  "status": "finished",
  "is_shareable": true,
  "headline": "Classic Central Beijing",
  "subheadline": "A light route through Beijing landmarks",
  "highlights": ["Tiananmen Square", "Forbidden City"],
  "route_style": "balanced",
  "guide_style": "SJ",
  "practical_tips": ["Go early for lighter crowds"],
  "trip_summary": {
    "itinerary_title": "Classic Central Beijing",
    "stop_count": 2,
    "stops_preview": ["Tiananmen Square", "Forbidden City"],
    "completed_at": "2026-04-15T12:00:00+00:00"
  },
  "social_summary": {
    "comment_count_total": 5,
    "featured_comment_preview": "Amazing views",
    "top_commented_stop_name": "Forbidden City"
  },
  "map_preview": {
    "polyline": [],
    "markers_preview": []
  }
}
```

Schema source:
- `src/yoyo/modules/share_card/schemas.py`

Important semantics:
- unfinished trips return `is_shareable=false`
- this is a frontend-facing read model, not the raw guide asset contract

---

## 12. QA

### `POST /api/v1/qa/ask`
Purpose:
- Main user Q&A entry point for supported Beijing tour questions.

Request body:
```json
{
  "guide_session_id": "guide_session_xxx",
  "user_id": "guest_xxx",
  "query": "What is my next stop?",
  "language": "en",
  "context": {}
}
```

Success response data shape:
```json
{
  "supported": true,
  "intent": "trip_assistant",
  "answer": "You are currently at Tiananmen Square. Your next stop is Forbidden City.",
  "used_skills": ["get_trip_context", "get_navigation_summary", "get_current_poi"],
  "metadata": {
    "context": {},
    "intent_router": {},
    "validation": {}
  }
}
```

Schema source:
- `src/yoyo/modules/qa/schemas.py` → `QAAskRequest`, `QAAskResponse`

Current QA scope:
- attraction explanation
- trip assistant / route guidance
- translation
- live info
- SQL-first + RAG fallback for deeper knowledge

Important current boundary:
- QA does **not** execute or hand off route changes in the current product path.
- Frontend should not treat QA responses as route-edit actions.
- Route changes must go through planning edit APIs.

Out-of-scope response behavior:
```json
{
  "supported": false,
  "intent": "out_of_scope",
  "answer": "I can help with Beijing tour topics such as attractions, itinerary guidance, translation, and travel info.",
  "used_skills": [],
  "metadata": {}
}
```

---

## 13. RAG admin

### `GET /api/v1/rag/index-runs/latest`
Purpose:
- Read the latest RAG index run.

Success response data shape:
```json
{
  "id": "run_xxx",
  "backend": "llamaindex_pgvector",
  "status": "succeeded",
  "reason": "ok",
  "availability": "ready",
  "document_count": 120,
  "collection_name": "yoyo_beijing",
  "payload": {
    "backend_status": {
      "ready": true,
      "enabled": true,
      "availability": "ready",
      "reason": "backend_ready"
    },
    "request": {},
    "operation": "rebuild_index",
    "execution_mode": "synchronous",
    "result": {
      "status": "succeeded",
      "reason": "ok",
      "availability": "ready"
    }
  },
  "error_message": null,
  "started_at": "2026-04-15T12:00:00+00:00",
  "finished_at": "2026-04-15T12:05:00+00:00"
}
```

### `POST /api/v1/rag/index-runs/rebuild`
Purpose:
- Trigger a RAG rebuild request.

Request body:
```json
{
  "poi_name": "Forbidden City",
  "doc_type": "guide_doc",
  "language": "en",
  "use_seed": false,
  "limit": 100
}
```

Success response data shape:
- same as `RAGIndexRunRead`

Schema source:
- `src/yoyo/modules/knowledge/rag_admin_schemas.py`

Notes:
- This is mainly an admin/internal interface, not a core first-phase user flow endpoint.
- Current implementation executes rebuild requests synchronously in the request path; `status` therefore reflects the finished outcome of that rebuild call rather than a detached background job poll state.
- Typical `availability` values are:
  - `disabled`: RAG is turned off intentionally
  - `misconfigured`: required DSN/key/runtime dependency is missing
  - `ready`: backend is configured enough to execute index/query work
- Typical `status` values are:
  - `running`: transient DB state used before the rebuild finishes
  - `skipped`: rebuild/query did not execute because the backend was disabled or misconfigured
  - `succeeded`: rebuild finished successfully
  - `failed` / `error`: runtime failure while building/querying

---

## 14. Suggested frontend integration order

### Golden path
1. `POST /api/v1/guest/sessions`
2. `GET /api/v1/questionnaire/flows/current`
3. `POST /api/v1/questionnaire/submissions`
4. choose one planning entry:
   - `GET /api/v1/planning/templates`
   - `POST /api/v1/planning/recommendations`
   - direct manual POI selection for itinerary creation
5. `POST /api/v1/planning/itineraries`
6. `POST /api/v1/session/guide`
7. `POST /api/v1/session/guide/{guide_session_id}/start`
8. `GET /api/v1/session/{guide_session_id}/current`
9. `GET /api/v1/map/session/{guide_session_id}`
10. during the trip:
    - `POST /api/v1/gps/update/{guide_session_id}`
    - `POST /api/v1/guide/playback/{guide_session_id}`
    - `POST /api/v1/guide/content/{guide_session_id}`
    - comments APIs as needed
11. route changes (manual only):
    - `POST /api/v1/planning/itineraries/{itinerary_id}/edits`
    - refresh session/map after success
12. end of trip:
    - `POST /api/v1/session/guide/{guide_session_id}/finish`
    - `GET /api/v1/share-card/session/{guide_session_id}`

---

## 15. Route-edit frontend checklist
- Always read `session current` before opening route-edit UI.
- Disable edits for stops before `current_stop_index`.
- Keep current stop editable.
- After any successful route edit:
  - refresh session current
  - refresh map session
  - refresh route details from itinerary if needed
- Do not treat GPS arrival as completion.
- Treat playback `complete` / `skip` as the progression trigger that moves the route boundary forward.
