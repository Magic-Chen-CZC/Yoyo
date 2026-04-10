# A Track Branch Notes

This document summarizes the branch `feature/a-track-stabilization-and-validation`.

## What this branch delivers
- Route editing for planner itineraries with version creation and history lookup.
- Session runtime stabilization around `current_stop_index`.
- GPS geofence arrival detection that triggers playback without auto-advancing stops.
- Playback-driven stop progression on `complete` and `skip`.
- Stable map payload fields that stay aligned with session current-state semantics.
- Acceptance validation coverage for A1-A5 and end-to-end chain verification.
- Live PostgreSQL enum compatibility fix plus migration for `guide_sessions.playback_state`.

## Main implementation areas
- Planner editing and version management:
  - `POST /api/v1/planning/itineraries/{itinerary_id}/edits`
  - `GET /api/v1/planning/itineraries/{itinerary_id}/versions`
- Session and GPS runtime:
  - `GET /api/v1/session/{guide_session_id}/current`
  - `POST /api/v1/gps/update/{guide_session_id}`
- Guide playback progression:
  - `POST /api/v1/guide/playback/{guide_session_id}`
- Map payload:
  - `GET /api/v1/map/session/{guide_session_id}`

## Behavioral decisions locked in on this branch
- Route edits always branch from the active itinerary version.
- `shorten_route` trims the route to a target stop count.
- GPS arrival only flips playback into a triggered state; it does not advance `current_stop_index`.
- Stop progression happens on playback `complete` or `skip`.
- Active sessions follow the latest itinerary version after a route edit, with safe stop remapping.
- Map `current_stop` and `next_stop` are derived from the same runtime rules as session current.

## Files to look at first
- Architecture and contracts:
  - `docs/architecture.md`
  - `docs/contracts.md`
  - `docs/todo.md`
- Route editing and session runtime:
  - `src/yoyo/modules/planner/service.py`
  - `src/yoyo/modules/planner/stop_catalog.py`
  - `src/yoyo/modules/session/runtime.py`
  - `src/yoyo/modules/session/service.py`
- Map and playback:
  - `src/yoyo/modules/map/service.py`
  - `src/yoyo/modules/guide/asset_service.py`
- Live DB compatibility fix:
  - `src/yoyo/db/enums.py`
  - `alembic/versions/0002_add_guide_playback_state.py`

## Validation on this branch
- Acceptance suite:
  - `.venv/bin/python scripts/run_a_validation.py`
- Repeated acceptance validation:
  - `.venv/bin/python scripts/run_a_validation.py --repeat 20 --concurrency 4`
- Live running service black-box validation:
  - `.venv/bin/python scripts/run_a_live_blackbox_stress.py --repeat 20 --concurrency 5`

## Latest verification snapshot
- A acceptance suite: `13/13` passed.
- Stress validation over repeated acceptance runs: passed.
- Live black-box stress against the running service: `20/20` passed after:
  - enum persistence was switched to use enum values instead of enum member names
  - migration `0002_add_guide_playback_state` was applied

## Notes for reviewers
- Generated files in `tests/reports/` are intentionally ignored and are not part of branch history.
- If you are testing from scratch, run migrations before starting the app:
  - `.venv/bin/alembic upgrade head`
- If the live app was already running before pulling this branch, restart `uvicorn` after dependency and migration sync.
