# Yoyo Documentation Index

This is the detailed document map for the current phase. The root `README.md` should stay short; topic details belong here or in the topic indexes below.

Current status: this pass creates indexes first and does not move the existing flat documents yet. Existing links keep working. A later cleanup can move files into the matching directories once the map is stable.

## Read First

1. [`../AGENTS.md`](../AGENTS.md) - repository working rules for AI sessions.
2. [`../README.md`](../README.md) - project overview and high-level entry points.
3. [`todo-phase-2.md`](todo-phase-2.md) - active todo.
4. [`phase-2-summary.md`](phase-2-summary.md) - active continuation summary.
5. [`dev-retrospective.md`](dev-retrospective.md) - problem / cause / improvement log.

## Project And Architecture

- [`architecture.md`](architecture.md) - backend architecture and core runtime decisions.
- [`contracts.md`](contracts.md) - shared contracts and cross-module ownership.
- [`collaboration.md`](collaboration.md) - collaboration split and shared files.
- [`dev-setup-for-teammates.md`](dev-setup-for-teammates.md) - local setup for teammates.
- [`project/README.md`](project/README.md) - project/phase document index.

## QA

- [`qa/README.md`](qa/README.md) - QA document entry point.
- [`qa/routing/README.md`](qa/routing/README.md) - intent routing, fallback, decision log.
- [`qa/intent-rules/README.md`](qa/intent-rules/README.md) - rule assets, keyword library, rule maintenance.
- [`qa/navigation/README.md`](qa/navigation/README.md) - navigation slots, Amap, place registry, clarification.
- [`qa/live-info/README.md`](qa/live-info/README.md) - live_info cache and same-day operation info.
- [`qa/translation/README.md`](qa/translation/README.md) - translator, Chinese pivot, multilingual QA.
- [`qa/prompts/README.md`](qa/prompts/README.md) - QA prompt versions and debugging notes.

## Testing And Evaluation

- [`testing/README.md`](testing/README.md) - feature tests, demo tests, readiness, test rounds.
- [`evals/README.md`](evals/README.md) - model evaluation, benchmark design, benchmark reports.
- [`feature-test-guide.md`](feature-test-guide.md) - feature-level testing overview.
- [`e2e-qa-benchmark.md`](e2e-qa-benchmark.md) - E2E QA benchmark method.
- [`eval-fields.md`](eval-fields.md) - benchmark result fields.

## Frontend And API

- [`frontend/README.md`](frontend/README.md) - frontend developer entry point.
- [`api-contracts-fullstack.md`](api-contracts-fullstack.md) - frontend/backend API contracts.

## Historical Or Track Docs

- [`tracks/README.md`](tracks/README.md) - A/B track and implementation-history docs.
- [`todo.md`](todo.md) - previous-phase todo archive.
- [`todo.zh-CN.md`](todo.zh-CN.md) - previous-phase Chinese reference.
- [`current-session-summary.md`](current-session-summary.md) - historical session log, not the active phase summary.

## Rule For Future Docs

- Put stable specs and maintenance rules in topic docs.
- Put benchmark outputs in `docs/evals/` or the matching topic report area.
- Keep current status in `phase-2-summary.md`.
- Keep progress and pending items in `todo-phase-2.md`.
- Keep issues, root-cause analysis, strategy changes, and durable fixes in `dev-retrospective.md`.
- Routine small tests do not need a `dev-retrospective.md` entry. Use it only when there is a real problem, a changed strategy, or a reusable improvement.
- When work changes project state, refresh `phase-2-summary.md` and `todo-phase-2.md`; add `dev-retrospective.md` only when the retrospective criteria above are met.
- Do not grow the root README with detailed benchmark history.
