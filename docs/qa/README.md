# QA Documents

This is the entry point for QA, routing, retrieval, generation, translation, live information, and navigation-text work.

## Recommended Reading

1. [`../qa-routing-strategy.md`](../qa-routing-strategy.md) - overall QA routing strategy.
2. [`../qa-rule-decision-log.md`](../qa-rule-decision-log.md) - lightweight record of recent rule decisions.
3. [`routing/README.md`](routing/README.md) - intent routing and fallback map.
4. [`intent-rules/README.md`](intent-rules/README.md) - rule assets and maintenance.
5. [`navigation/README.md`](navigation/README.md) - navigation-specific slots, Amap, and clarification.

## QA Subsystems

- Routing and fallback: [`routing/README.md`](routing/README.md)
- Intent rules and keyword assets: [`intent-rules/README.md`](intent-rules/README.md)
- Navigation text: [`navigation/README.md`](navigation/README.md)
- Live info cache: [`live-info/README.md`](live-info/README.md)
- Translation and Chinese pivot: [`translation/README.md`](translation/README.md)
- Prompts and prompt debugging: [`prompts/README.md`](prompts/README.md)

## Current Runtime Shape

```text
raw query
-> translator preprocess when needed
-> Chinese intent rules
-> router fallback for ambiguous cases
-> handler-specific context building
-> SQL / RAG / live_info / weather / navigation / generation
-> answer postprocess
```

## Maintenance Rule

When QA behavior changes, update the most specific topic doc first, then refresh [`../qa-rule-decision-log.md`](../qa-rule-decision-log.md) and the root/index docs only if the entry point changes.
