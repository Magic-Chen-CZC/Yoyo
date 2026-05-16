# QA Live Info Documents

This folder indexes live same-day attraction operation information.

## Core Docs

- [`../../qa-live-info-cache.md`](../../qa-live-info-cache.md) - Redis-backed cache design for `live_info`.
- [`../../qa-rule-decision-log.md`](../../qa-rule-decision-log.md) - QA-RULE-006 and related decisions.

## Runtime Files

- `src/yoyo/modules/qa/live_info.py`
- `src/yoyo/modules/qa/live_info_cache.py`
- `src/yoyo/modules/qa/live_search.py`
- `src/yoyo/modules/knowledge/live_retriever.py`

## Boundary

`live_info` is only for same-day or near-time official operation facts: opening, closing, tickets, reservation, inspection, temporary notices. Traffic, crowding, parking, air quality, and booking/payment execution remain boundary or unsupported cases unless product scope changes.
