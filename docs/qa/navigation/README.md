# Navigation QA Documents

This folder indexes the `navigation_text` intent: slot extraction, place resolution, Amap calls, walking/transit formatting, multi-leg aggregation, and clarification.

## Core Docs

- [`../../navigation-slot-routing-design.md`](../../navigation-slot-routing-design.md) - source of truth for navigation slots and routing behavior.
- [`../../navigation-slot-benchmark-2026-05-15.md`](../../navigation-slot-benchmark-2026-05-15.md) - slot benchmark report.
- [`../../navigation-hard-300-amap-benchmark-2026-05-15.md`](../../navigation-hard-300-amap-benchmark-2026-05-15.md) - real Amap hard benchmark report.
- [`../../qa-rule-decision-log.md`](../../qa-rule-decision-log.md) - QA-RULE navigation decisions.

## Runtime Files

- `src/yoyo/modules/knowledge/place_resolver.py`
- `src/yoyo/modules/knowledge/navigation_place_registry_generated.py`
- `src/yoyo/modules/knowledge/navigation_retriever.py`
- `src/yoyo/modules/knowledge/hybrid_context_builder.py`
- `src/yoyo/modules/integrations/amap/client.py`
- `src/yoyo/modules/qa/formatters.py`
- `src/yoyo/modules/qa/orchestrator.py`

## Evaluation Assets

- `evals/run_navigation_benchmark.py`
- `evals/run_navigation_turnpoint_smoke.py`
- `evals/build_navigation_place_registry.py`
- `evals/datasets/navigation_slot_100_cases.json`
- `evals/datasets/navigation_slot_complex_100_cases.json`
- `evals/datasets/navigation_slot_hard_300_cases.json`
- `evals/results/navigation_place_registry_geocode_20260516.json`

## Current Principles

- Registered Beijing tourism POIs use local coordinates first.
- Low-confidence or commercial/address-ambiguous locations clarify before route planning.
- Multi-leg routes are split into consecutive two-point Amap calls and then aggregated.
- Explicit travel mode wins. Unspecified mode defaults by straight-line distance: over 3 km transit, otherwise walking.
- Transit empty results fall back to walking with user-facing wording that says there is no suitable public transit route.
