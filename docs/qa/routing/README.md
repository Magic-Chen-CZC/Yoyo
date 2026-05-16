# QA Routing Documents

This folder indexes the intent routing layer: high-precision rules, model fallback, conflict handling, and routing evaluation.

## Core Docs

- [`../../qa-routing-strategy.md`](../../qa-routing-strategy.md) - overall routing architecture.
- [`../../qa-rule-decision-log.md`](../../qa-rule-decision-log.md) - recent QA rule decisions.
- [`../../qa-routing-root-cause-and-fix.md`](../../qa-routing-root-cause-and-fix.md) - historical routing root-cause notes.
- [`../../router-fallback-zh-prompt-template.md`](../../router-fallback-zh-prompt-template.md) - router fallback prompt template.
- [`../../routing-model-selection-plan.md`](../../routing-model-selection-plan.md) - routing-model selection and multilingual strategy.

## Benchmark Reports

- [`../../routing-zh-hard-benchmark-report-2026-05-08.md`](../../routing-zh-hard-benchmark-report-2026-05-08.md) - zh-hard routing model comparison.
- [`../../routing-rule-maintenance-benchmark-2026-05-15.md`](../../routing-rule-maintenance-benchmark-2026-05-15.md) - 100-case maintenance benchmark.
- [`../../routing-rule-complex-benchmark-2026-05-15.md`](../../routing-rule-complex-benchmark-2026-05-15.md) - 200 complex / 300 combined report.
- [`../../routing-rule-hard-500-benchmark-2026-05-15.md`](../../routing-rule-hard-500-benchmark-2026-05-15.md) - 500 hard / 800 combined report.

## Runtime Files

- `src/yoyo/modules/qa/intent_router.py`
- `src/yoyo/modules/qa/router_fallback.py`
- `src/yoyo/modules/qa/domain_guard.py`
- `src/yoyo/modules/qa/rule_assets.py`

## Maintenance Principle

Rules direct-pass only high-confidence cases. Ambiguous, multi-intent, or low-evidence queries should go to router fallback instead of expanding brittle keyword matches.
