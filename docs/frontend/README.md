# Frontend Development Docs

This directory is the entry point for frontend developers working against the Yoyo backend.

## Read in this order
1. [`../api-contracts-fullstack.md`](../api-contracts-fullstack.md) — the current frontend/backend API contract, request/response examples, runtime state semantics, and integration order.
2. [`../dev-setup-for-teammates.md`](../dev-setup-for-teammates.md) — local setup, environment variables, startup commands, and test commands.
3. [`../test-readiness-checklist.md`](../test-readiness-checklist.md) — the recommended frontend/backend integration verification order and minimum smoke path.
4. [`../demo-test-plan.md`](../demo-test-plan.md) — full test coverage, scenarios, and priorities for demo or release validation.
5. [`../contracts.md`](../contracts.md) — shared ownership and runtime semantics that matter when frontend depends on route/session/guide boundaries.

## Which document owns what
- API fields, request/response examples, route-edit semantics, and runtime state meanings live in [`../api-contracts-fullstack.md`](../api-contracts-fullstack.md).
- Environment setup, `.env`, infra, and startup commands live in [`../dev-setup-for-teammates.md`](../dev-setup-for-teammates.md).
- Integration verification order and smoke checks live in [`../test-readiness-checklist.md`](../test-readiness-checklist.md).
- Full testing scope and scenario coverage live in [`../demo-test-plan.md`](../demo-test-plan.md).
- Shared ownership and cross-module boundaries live in [`../contracts.md`](../contracts.md).

## Frontend implementation checklist
- Start with the onboarding and trip golden path in `api-contracts-fullstack.md`.
- Use `session current` and `map session` as the runtime source of truth.
- Treat route editing as manual-only and route-edit APIs as the only write path for route changes.
- Do not derive route-edit permissions from old assumptions; prefer the editability fields returned by the runtime APIs.
- Use the readiness checklist before calling a feature integration complete.
