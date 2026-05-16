# QA Prompt Documents

This folder indexes prompt versions, prompt debugging notes, and model-specific prompt constraints.

## Core Docs

- [`../../qa-prompt-debugging.md`](../../qa-prompt-debugging.md) - QA prompt debugging notes.
- [`../../qa-prompt-doubao-v4.md`](../../qa-prompt-doubao-v4.md) - Doubao Mini v4 QA prompt.
- [`../../router-fallback-zh-prompt-template.md`](../../router-fallback-zh-prompt-template.md) - router fallback prompt template.

## Runtime Files

- `src/yoyo/modules/qa/prompts.py`
- `src/yoyo/modules/qa/generator.py`
- `src/yoyo/modules/qa/router_fallback.py`

## Maintenance Principle

Prompt docs should describe the intended contract and failure modes. Runtime behavior still needs tests for JSON structure, fallback behavior, grounding, and latency metadata.
