# QA Translation Documents

This folder indexes translation as both a user-facing QA ability and a routing preprocessor.

## Core Docs

- [`../../translation-benchmark-summary-2026-05-07.md`](../../translation-benchmark-summary-2026-05-07.md) - translation benchmark summary.
- [`../../routing-model-selection-plan.md`](../../routing-model-selection-plan.md) - multilingual routing and Chinese pivot plan.
- [`../../feature-test-guide.md`](../../feature-test-guide.md) - translator feature testing section.
- [`../../qa-intent-routing-rule-design.md`](../../qa-intent-routing-rule-design.md) - Chinese pivot rule constraint.

## Runtime Files

- `src/yoyo/modules/translator/`
- `src/yoyo/modules/qa/orchestrator.py`
- `src/yoyo/modules/qa/intent_router.py`

## Benchmark Assets

- `evals/run_translation_eval.py`
- `evals/datasets/translation_models_product.yaml`
- `evals/datasets/translation_models_routing.yaml`

## Current Principles

- Foreign and Southeast Asian language queries pivot to Chinese before intent rules.
- Explicit translation requests preserve `raw_query` so the text to translate is not lost after pivoting.
- XFYun ITS is the current default production translator; HY-MT remains historical benchmark data.
