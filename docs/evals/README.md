# Evaluation Documents

This folder indexes benchmark design, model evaluation, result fields, and major benchmark reports.

## Core Docs

- [`../model-evaluation.md`](../model-evaluation.md) - model evaluation plan and dimensions.
- [`../eval-fields.md`](../eval-fields.md) - per-case and summary output fields.
- [`../e2e-qa-benchmark.md`](../e2e-qa-benchmark.md) - E2E QA benchmark method.
- [`../round1-model-selection-summary.md`](../round1-model-selection-summary.md) - round 1 model selection summary.
- [`../gemini-round2-summary.md`](../gemini-round2-summary.md) - Gemini round 2 summary.

## Current QA Benchmark Reports

- [`../e2e-qa-intent-hard-1800-qwen-2026-05-16.md`](../e2e-qa-intent-hard-1800-qwen-2026-05-16.md)
- [`../navigation-hard-300-amap-benchmark-2026-05-15.md`](../navigation-hard-300-amap-benchmark-2026-05-15.md)
- [`../navigation-slot-benchmark-2026-05-15.md`](../navigation-slot-benchmark-2026-05-15.md)
- [`../routing-rule-hard-500-benchmark-2026-05-15.md`](../routing-rule-hard-500-benchmark-2026-05-15.md)
- [`../translation-benchmark-summary-2026-05-07.md`](../translation-benchmark-summary-2026-05-07.md)

## Main Runners

- `evals/run_e2e_qa_benchmark.py`
- `evals/run_routing_benchmark.py`
- `evals/run_routing_candidate_sweep.py`
- `evals/run_navigation_benchmark.py`
- `evals/run_translation_eval.py`
- `evals/export_excel.py`

## Artifact Rule

Use docs for methodology, summaries, and interpretation. Keep raw JSON, CSV, and Excel outputs under `evals/results/`.
