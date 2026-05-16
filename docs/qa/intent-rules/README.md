# QA Intent Rule Documents

This folder indexes the maintainable intent rule layer: keyword libraries, phrase/pattern rules, conflict rules, and regression datasets.

## Core Docs

- [`../../qa-intent-routing-rule-design.md`](../../qa-intent-routing-rule-design.md) - rule-router design.
- [`../../qa-intent-keyword-library.yaml`](../../qa-intent-keyword-library.yaml) - maintained intent keyword/policy library.
- [`../../qa-intent-rule-maintenance.md`](../../qa-intent-rule-maintenance.md) - daily maintenance process.
- [`../../qa-rule-decision-log.md`](../../qa-rule-decision-log.md) - rule decisions and maintenance locations.

## Datasets

- `evals/datasets/routing_rule_maintenance_100_cases.yaml`
- `evals/datasets/routing_rule_complex_200_cases.yaml`
- `evals/datasets/routing_rule_hard_500_cases.yaml`
- `evals/datasets/routing_rule_all_800_cases.yaml`

## Benchmark Reports

- [`../../routing-rule-maintenance-benchmark-2026-05-15.md`](../../routing-rule-maintenance-benchmark-2026-05-15.md)
- [`../../routing-rule-complex-benchmark-2026-05-15.md`](../../routing-rule-complex-benchmark-2026-05-15.md)
- [`../../routing-rule-hard-500-benchmark-2026-05-15.md`](../../routing-rule-hard-500-benchmark-2026-05-15.md)

## Rule Boundary

All non-Chinese queries pivot to Chinese before rules run. The rule library should therefore maintain one Chinese lexicon and one Chinese conflict strategy, while preserving raw query and translation metadata for debugging.
