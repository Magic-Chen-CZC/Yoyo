# Yoyo Todo (Archive v1)

## Phase 1: bootstrap
- [x] Create repo scaffold and project metadata
- [x] Add local infra files and env example
- [x] Create FastAPI app factory and API router skeleton
- [x] Create config, logging, DB session, Redis wiring
- [x] Set up Alembic base files

## Phase 2: data model
- [x] Add shared enums
- [x] Add questionnaire submission model
- [x] Add itinerary model
- [x] Add itinerary version model
- [x] Add guide generation job model
- [x] Add guide session model
- [x] Add QA message model
- [x] Create initial Alembic migration

## Phase 3: first vertical slice
- [x] Add health endpoint
- [x] Add questionnaire submission endpoint
- [x] Add planning create itinerary endpoint
- [x] Add itinerary detail endpoint
- [x] Add guide job create endpoint
- [x] Add guide job detail endpoint
- [x] Implement deterministic planner v0
- [x] Implement guide job enqueue logic
- [x] Implement ARQ worker task
- [x] Add tests for first vertical slice

## Later
- [x] Controlled single-agent Guide QA skeleton
- [x] Replace QA placeholders with session-aware context and first real route-aware responses
- [x] Make guide generation worker persist status/result updates
- [x] Add retrieval-backed QA skills and live-info source handling
- [x] Map/session/GPS APIs
- [x] Guide asset retrieval and playback state
- [x] Model evaluation harness
- [ ] Add stronger evaluation rubrics and comparative report generation
