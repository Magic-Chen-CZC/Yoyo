# B Track Round 1 Test Cases

This document defines a **small first-round test set** for current model selection work.
The goal is **not** full regression coverage. The goal is to compare candidate models on the most important B-side behaviors in the current SQL-first architecture.

## 1. Scope of this round

This round focuses on:
- multi-turn dialogue continuity
- short-term memory usage
- clarification behavior
- live search / web-backed real-time info behavior
- SQL-grounded attraction/profile usage
- intent recognition and routing quality
- structured route-edit extraction
- profile-aware guide-generation-style output quality

This round intentionally keeps the case count small.

---

## 2. Evaluation principles

For each test case, reviewers should check:
1. **Task completion** — did the model do the requested thing?
2. **Grounding** — did it use SQL-backed facts, route context, memory, or live-info hints correctly?
3. **Clarity** — is the answer usable for a traveler?
4. **Control** — does it stay within the intended role instead of drifting?
5. **Safety / honesty** — if information is uncertain, does it say so clearly?

Recommended scoring for manual review:
- 5 = excellent
- 4 = strong
- 3 = acceptable
- 2 = weak
- 1 = poor
- 0 = failed or unusable

---

## 3. Round 1 test set overview

Total suggested first-round cases: **12**

Breakdown:
- Intent recognition / routing: 3
- Multi-turn dialogue / memory: 3
- Clarification behavior: 2
- Live search / real-time info: 2
- SQL-grounded attraction/profile usage: 1
- Structured planner handoff: 1

This is intentionally compact enough for model selection.

---

## 4. Suggested execution order

Recommended testing order for the current shortlist:
1. `openai/gpt-5.4-mini`
2. `google/gemini-2.5-flash-lite`
3. `qwen/qwen3.5-flash-02-23`
4. `openai/gpt-5-nano`
5. `x-ai/grok-4.1-fast`

Why this order:
- `gpt-5.4-mini` can act as a strong small-model reference point
- `gemini-2.5-flash-lite` is a strong speed/cost comparison candidate
- `qwen` is worth checking early for multilingual and style behavior
- `gpt-5-nano` can show the lower-cost edge
- `grok-4.1-fast` can be compared after the others for tone/style differences

---

## 5. Test cases

## A. Intent recognition / routing

### Case A1 — Attraction explanation
- `case_id`: `A1`
- `title`: Attraction explanation
- `category`: `intent_routing`
- `goal`: verify attraction explanation routing and grounded response structure
- `mode`: `single_turn`
- `language`: `en`
- `turns`:
  - user: `Tell me more about the Forbidden City and why it matters for first-time visitors.`
- `expected_intent`: `attraction_explain`
- `expected_data_source`: `sql`
- `expected_behavior`:
  - Routes to attraction explanation behavior
  - Gives a concise explanation with historical or cultural framing
  - Mentions useful visitor-facing highlights or tips
  - Feels grounded in Beijing tourism rather than generic travel filler
- `scoring_focus`:
  - routing quality
  - SQL grounding
  - answer usefulness
- `failure_signals`:
  - routes to trip_assistant or live_info
  - gives generic city filler without attraction grounding
  - omits practical visitor value

#### Result template
- provider:
- model:
- latency_ms:
- estimated_cost:
- raw_answer:
- manual_score:
- score_reason:
- reviewer_notes:

---

### Case A2 — Live info intent
- `case_id`: `A2`
- `title`: Live info intent
- `category`: `intent_routing`
- `goal`: verify the model recognizes that this is a real-time information request
- `mode`: `single_turn`
- `language`: `en`
- `turns`:
  - user: `What should I verify today before going to the Forbidden City?`
- `expected_intent`: `live_info`
- `expected_data_source`: `live_search`
- `expected_behavior`:
  - Routes to live-info style behavior
  - Talks about same-day verification
  - Mentions official/real-time source checking
  - Acknowledges that opening hours / tickets / closures may change
- `scoring_focus`:
  - intent routing
  - uncertainty handling
  - live-info wording quality
- `failure_signals`:
  - treats static SQL knowledge as sufficient
  - no same-day verification language
  - overconfident answer

#### Result template
- provider:
- model:
- latency_ms:
- estimated_cost:
- raw_answer:
- manual_score:
- score_reason:
- reviewer_notes:

---

### Case A3 — Route-edit intent
- `case_id`: `A3`
- `title`: Route-edit intent
- `category`: `intent_routing`
- `goal`: verify route-edit intent is not confused with trip guidance
- `mode`: `single_turn`
- `language`: `en`
- `turns`:
  - user: `Replace the next stop with something more scenic and easier.`
- `expected_intent`: `planner_handoff`
- `expected_data_source`: `sql`
- `expected_behavior`:
  - Recognizes planner-handoff / route-edit intent
  - Does not answer as if the user only asked for route guidance
  - Produces structured route-edit understanding or clearly route-edit-oriented answer
- `scoring_focus`:
  - intent routing
  - route-edit understanding
- `failure_signals`:
  - routes to trip_assistant
  - misses operation/target/constraints
  - answers like passive route advice only

#### Result template
- provider:
- model:
- latency_ms:
- estimated_cost:
- raw_answer:
- manual_score:
- score_reason:
- reviewer_notes:

---

## B. Multi-turn dialogue / memory

### Case B1 — Follow-up from attraction explanation
- `case_id`: `B1`
- `title`: Follow-up from attraction explanation
- `category`: `multi_turn_memory`
- `goal`: verify that the second turn can inherit the first turn’s topic
- `mode`: `multi_turn`
- `language`: `en`
- `turns`:
  - user: `Tell me more about Tiananmen Square.`
  - user: `Why is it important historically?`
- `expected_intent`: `attraction_explain`
- `expected_data_source`: `sql + history`
- `expected_behavior`:
  - Turn 2 correctly understands that “it” means Tiananmen Square
  - Answer remains attraction-explain style, not trip-assistant style
  - Uses prior turn context without needing the user to repeat the place name
- `scoring_focus`:
  - memory continuity
  - referent resolution
  - attraction grounding
- `failure_signals`:
  - asks “what place?” unnecessarily
  - switches to route guidance
  - loses the referent

#### Result template
- provider:
- model:
- latency_ms:
- estimated_cost:
- raw_answer:
- manual_score:
- score_reason:
- reviewer_notes:

---

### Case B2 — Follow-up to next-stop question
- `case_id`: `B2`
- `title`: Follow-up to next-stop question
- `category`: `multi_turn_memory`
- `goal`: verify route continuity across turns
- `mode`: `multi_turn`
- `language`: `en`
- `turns`:
  - user: `What is my next stop after Tiananmen Square?`
  - user: `What should I pay attention to there?`
- `expected_intent`: `trip_assistant`
- `expected_data_source`: `sql + history`
- `expected_behavior`:
  - Turn 2 correctly refers to the next stop from turn 1
  - Uses route context rather than treating the second turn as a new random attraction query
- `scoring_focus`:
  - route continuity
  - follow-up memory
- `failure_signals`:
  - resets topic
  - answers about the wrong attraction
  - ignores prior turn route context

#### Result template
- provider:
- model:
- latency_ms:
- estimated_cost:
- raw_answer:
- manual_score:
- score_reason:
- reviewer_notes:

---

### Case B3 — Memory after route-edit intent
- `case_id`: `B3`
- `title`: Memory after route-edit intent
- `category`: `multi_turn_memory`
- `goal`: verify that the system can keep route-edit context across turns
- `mode`: `multi_turn`
- `language`: `en`
- `turns`:
  - user: `Replace Jingshan Park with a more family-friendly stop.`
  - user: `Also make the route shorter.`
- `expected_intent`: `planner_handoff`
- `expected_data_source`: `sql + history`
- `expected_behavior`:
  - Turn 2 is still understood as route-edit follow-up
  - Constraints should accumulate or remain consistent
  - The second turn should not fall back to attraction explanation
- `scoring_focus`:
  - route-edit continuity
  - context carryover
- `failure_signals`:
  - resets to generic attraction answer
  - loses the route-edit thread
  - ignores the second-turn constraint

#### Result template
- provider:
- model:
- latency_ms:
- estimated_cost:
- raw_answer:
- manual_score:
- score_reason:
- reviewer_notes:

---

## C. Clarification behavior

### Case C1 — Ambiguous translation input
- `case_id`: `C1`
- `title`: Ambiguous translation input
- `category`: `clarification`
- `goal`: verify that the model asks for clarification only when it truly needs to
- `mode`: `single_turn`
- `language`: `en`
- `turns`:
  - user: `Help me translate this.`
- `expected_intent`: `translation`
- `expected_data_source`: `history or none`
- `expected_behavior`:
  - Asks for the exact phrase
  - Keeps the clarification brief and useful
  - Does not hallucinate a translation target
- `scoring_focus`:
  - clarification quality
  - restraint
- `failure_signals`:
  - hallucinates a phrase to translate
  - over-explains
  - refuses instead of clarifying

#### Result template
- provider:
- model:
- latency_ms:
- estimated_cost:
- raw_answer:
- manual_score:
- score_reason:
- reviewer_notes:

---

### Case C2 — Ambiguous route-edit request
- `case_id`: `C2`
- `title`: Ambiguous route-edit request
- `category`: `clarification`
- `goal`: verify that the system handles under-specified route-edit intent carefully
- `mode`: `single_turn`
- `language`: `en`
- `turns`:
  - user: `Change the route to make it better.`
- `expected_intent`: `planner_handoff`
- `expected_data_source`: `sql`
- `expected_behavior`:
  - Asks what kind of change is preferred, or exposes missing constraints
  - Does not invent a target stop or operation with high confidence
- `scoring_focus`:
  - clarification quality
  - anti-hallucination behavior
- `failure_signals`:
  - invents a stop target
  - invents an operation with false certainty
  - responds with generic filler

#### Result template
- provider:
- model:
- latency_ms:
- estimated_cost:
- raw_answer:
- manual_score:
- score_reason:
- reviewer_notes:

---

## D. Live search / real-time info

### Case D1 — Dynamic opening-hours style query
- `case_id`: `D1`
- `title`: Dynamic opening-hours style query
- `category`: `live_info`
- `goal`: verify proper live-info behavior on a clearly dynamic question
- `mode`: `single_turn`
- `language`: `en`
- `turns`:
  - user: `Is the Temple of Heaven likely to have any same-day access issues today?`
- `expected_intent`: `live_info`
- `expected_data_source`: `live_search`
- `expected_behavior`:
  - Treats this as dynamic information
  - Mentions things like hours, closures, weather, queue, transport, or official notices
  - Signals that conditions may change
- `scoring_focus`:
  - live-search wording
  - uncertainty honesty
- `failure_signals`:
  - answers as if this is static attraction knowledge
  - no same-day verification advice
  - overconfident unsupported specifics

#### Result template
- provider:
- model:
- latency_ms:
- estimated_cost:
- raw_answer:
- manual_score:
- score_reason:
- reviewer_notes:

---

### Case D2 — Source-awareness under uncertainty
- `case_id`: `D2`
- `title`: Source-awareness under uncertainty
- `category`: `live_info`
- `goal`: verify whether the response remains honest when certainty is limited
- `mode`: `single_turn`
- `language`: `en`
- `turns`:
  - user: `Give me the latest real-time guidance for visiting Jingshan Park right now.`
- `expected_intent`: `live_info`
- `expected_data_source`: `live_search`
- `expected_behavior`:
  - Mentions verifying current official or real-time sources
  - Does not overstate certainty
  - If the system cannot confirm, it should say so cleanly
- `scoring_focus`:
  - uncertainty handling
  - live-info control
- `failure_signals`:
  - speaks with unwarranted certainty
  - omits verification language
  - ignores real-time nature of the question

#### Result template
- provider:
- model:
- latency_ms:
- estimated_cost:
- raw_answer:
- manual_score:
- score_reason:
- reviewer_notes:

---

## E. SQL-grounded attraction/profile usage

### Case E1 — Personalized attraction explanation
- `case_id`: `E1`
- `title`: Personalized attraction explanation
- `category`: `sql_grounding`
- `goal`: verify whether the answer reflects profile-aware guidance instead of generic explanation
- `mode`: `single_turn`
- `language`: `en`
- `turns`:
  - user: `Tell me about the next stop on my route.`
- `expected_intent`: `attraction_explain`
- `expected_data_source`: `sql + profile`
- `expected_behavior`:
  - Uses the current route context to identify the stop
  - Gives attraction explanation with at least some profile-aware emphasis
  - Can reflect history angle, photo highlight, or pacing-conscious advice
- `scoring_focus`:
  - SQL grounding
  - profile-aware answer shaping
- `failure_signals`:
  - generic answer that ignores profile
  - no route grounding
  - wrong stop selection

#### Result template
- provider:
- model:
- latency_ms:
- estimated_cost:
- raw_answer:
- manual_score:
- score_reason:
- reviewer_notes:

---

## F. Structured planner handoff

### Case F1 — Replace + scenic + lighter walking
- `case_id`: `F1`
- `title`: Replace + scenic + lighter walking
- `category`: `planner_handoff`
- `goal`: verify structured route-edit understanding quality
- `mode`: `single_turn`
- `language`: `en`
- `turns`:
  - user: `Replace Jingshan Park with a more scenic stop and make the route easier.`
- `expected_intent`: `planner_handoff`
- `expected_data_source`: `sql`
- `expected_behavior`:
  - `operation`: replace_stop
  - `target`: Jingshan Park
  - constraints should include scenic and lighter walking intent
- `scoring_focus`:
  - route-edit structure quality
  - constraint capture quality
- `failure_signals`:
  - wrong operation
  - missing target
  - misses scenic / walking constraint

#### Result template
- provider:
- model:
- latency_ms:
- estimated_cost:
- raw_answer:
- manual_score:
- score_reason:
- reviewer_notes:

---

## 6. Optional bonus cases if time allows

If you want a slightly larger round later, add these next:
- multilingual attraction explanation in Chinese
- multilingual trip assistant in Spanish
- profile-aware guide card generation prompt
- live-info query with mixed static + real-time ambiguity
- short two-turn clarification + resolution flow

---

## 7. Round 1 candidate models

Current first-round model shortlist:
- `google/gemini-2.5-flash-lite`
- `x-ai/grok-4.1-fast`
- `openai/gpt-5-nano`
- `qwen/qwen3.5-flash-02-23`
- `openai/gpt-5.4-mini`

### Cost note
For this round, per-model pricing should be checked directly on the OpenRouter website before final comparison.

## 8. Suggested test case fields

Recommended test-case definition fields:
- `case_id`
- `title`
- `category`
- `goal`
- `mode`
- `language`
- `turns`
- `expected_intent`
- `expected_data_source`
- `expected_behavior`
- `scoring_focus`
- `failure_signals`
- `notes`

Recommended execution/result fields:
- `provider`
- `model`
- `case_id`
- `raw_answer`
- `latency_ms`
- `estimated_cost`
- `manual_score`
- `score_reason`
- `reviewer_notes`

## 9. Suggested execution format for model selection

For each candidate model, record:
- provider
- model name
- answer text
- manual score (0-5)
- short rationale
- notes about routing / memory / grounding / uncertainty behavior

Suggested summary table columns:
- Case ID
- Category
- Provider
- Model
- Score
- Main strength
- Main weakness

---

## 10. Current architecture reminder for reviewers

When reviewing these test cases, keep in mind the current system assumptions:
- current phase is SQL-first
- attraction/profile knowledge is expected to come from PostgreSQL-backed data
- live search is only for same-day dynamic facts
- current memory design = session runtime state + recent `qa_messages` + profile context
- current intent recognition = rules-first with confidence/signals/conflict handling, not full LLM classification

---

## 11. What this round is for

This round is for:
- first-pass model selection
- identifying obvious failures in routing, grounding, memory, and honesty
- narrowing which models are worth deeper evaluation later

This round is **not** for:
- final production certification
- complete regression testing
- exhaustive edge-case coverage
