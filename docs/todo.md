# Yoyo Todo

This is the active todo list after splitting work into A/B tracks.

---

## Shared / coordination
- [x] Write shared overlap contracts into `docs/contracts.md`
- [x] Freeze shared `itinerary_version.plan_json` contract in `docs/architecture.md`
- [x] Freeze shared `guide_generation_job.result_json` contract in `docs/architecture.md`
- [x] Freeze shared `guide_session.context_json` field ownership in `docs/architecture.md`
- [x] Freeze `session current` response contract in `docs/architecture.md`
- [x] Define GPS -> guide trigger handoff behavior in `docs/architecture.md`
- [x] Define `planner_handoff` structured payload contract in `docs/architecture.md`
- [x] Decide migration ownership rule for the next schema changes
- [x] Keep `api/router.py` wiring changes small and late
- [x] Finish all remaining shared contracts above before broad QA verification

---

## A track: Planner / Session / Map / GPS

### A1. Route editing and version management
- [ ] Add route edit request schema
- [ ] Implement replace stop operation
- [ ] Implement remove stop operation
- [ ] Implement reorder stop operation
- [ ] Implement shorten route operation
- [ ] Create new `itinerary_version` on each edit
- [ ] Switch active itinerary version after edit
- [ ] Keep prior versions queryable
- [ ] Add tests for version switching

### A2. Session runtime state
- [ ] Add `current_stop_index` to session runtime model
- [ ] Stop assuming current stop is always the first stop
- [ ] Compute current stop from session state
- [ ] Compute next stop from session state
- [ ] Add tests for session progression

### A3. GPS and geofence
- [ ] Add first distance calculation helper
- [ ] Add per-stop arrival threshold
- [ ] Mark arrived when user enters threshold
- [ ] Update session runtime when arriving at a stop
- [ ] Prepare trigger signal for guide playback
- [ ] Add tests for geofence logic

### A4. Map payload improvements
- [ ] Guarantee stable marker fields
- [ ] Guarantee stable polyline fields
- [ ] Align current/next stop with `current_stop_index`
- [ ] Expose frontend-friendly navigation summary
- [ ] Add map payload tests

### A5. Contract hygiene
- [x] Ensure every stop has `name/category/latitude/longitude/recommended_duration_minutes`
- [x] Update `docs/architecture.md` when stop contract changes

---

## B track: Guide / QA / Retrieval / Eval

### B1. QA quality upgrades
- [x] Make `planner_handoff` return structured route-edit intent
- [x] Strengthen `trip_assistant` route-aware answers
- [x] Strengthen `attraction_explain` answer formatting
- [x] Improve `translation` outputs beyond placeholder mode
- [x] Add category-specific answer formatting tests

### B2. Live-info provider integration
- [x] Introduce live-info provider abstraction
- [x] Add provider-backed source records
- [x] Preserve `updated_at` and source metadata in responses
- [x] Add graceful failure / not-confirmed behavior
- [x] Add tests for source-bearing live-info responses

### B3. Guide generation enrichment
- [x] Expand `result_json` to include guide script payload
- [x] Expand `result_json` to include card payload
- [x] Prepare TTS-ready output fields
- [x] Add tests for enriched guide generation output

### B4. Playback and guide asset improvements
- [x] Connect gps trigger action to playback transitions
- [x] Add `trigger` flow coverage in tests
- [x] Add richer playback metadata in session context
- [ ] Ensure active guide asset always reflects latest successful version

### B5. Model evaluation improvements
- [x] Batch query generation
- [x] Multi-provider eval runner
- [x] Cost/latency summary
- [x] Basic rubric scoring
- [x] Batch multi-model run support
- [x] English 81-query dataset
- [ ] Add stronger rubrics per category
- [ ] Add comparative markdown report generation
- [ ] Add category breakdown report
- [ ] Add per-model ranking output
- [ ] Run first real benchmark on selected models

### B6. First real benchmark execution
- [ ] Prepare `.env` with provider keys
- [ ] Confirm first benchmark matrix
- [ ] Run English 81-query batch for shortlisted models
- [ ] Save results to `evals/results/`
- [ ] Summarize latency/cost/score comparison

---

## Current recommendation
- A continues on route/runtime state and version progression
- B continues on guide/QA/eval and model-selection work
