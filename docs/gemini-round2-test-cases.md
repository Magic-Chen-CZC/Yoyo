# Gemini 2.5 Flash Lite — Round 2 Focused Test Cases

This document defines the **second-round focused test set** for:
- `google/gemini-2.5-flash-lite`

Goal:
- validate whether it is strong enough to serve as the default model for the current SQL-first Yoyo B stack
- go deeper on the areas that matter most after round 1

This round is intentionally more focused than round 1.

---

## 1. Why Gemini moves to round 2

Round 1 findings:
- overall score: **4.25**
- fastest average latency among tested models
- lowest estimated total cost among tested models
- strong on:
  - `live_info`
  - `trip_assistant`
- acceptable but not yet dominant on:
  - `translation`
  - `planner_handoff`
  - `attraction_explain`

So round 2 should stress:
1. memory continuity under more realistic follow-ups
2. clarification quality on underspecified requests
3. planner_handoff precision on edge cases
4. profile-aware guide tone stability
5. SQL grounding discipline under more complex prompts

---

## 2. Round 2 test set overview

Suggested total cases: **10**

Breakdown:
- Multi-turn continuity: 3
- Clarification quality: 2
- Planner handoff precision: 2
- Profile-aware guide/QA style control: 2
- SQL grounding discipline: 1

---

## 3. Test cases

## A. Multi-turn continuity

### Case R2-A1 — Pronoun carryover after attraction explanation
- `case_id`: `R2-A1`
- `category`: `multi_turn_memory`
- `goal`: ensure the model can maintain referents over a short two-turn attraction conversation
- `turns`:
  - user: `Tell me more about the Forbidden City.`
  - user: `Why was it so important politically?`
- `expected_behavior`:
  - resolves `it` correctly as Forbidden City
  - gives historical-political framing
  - does not reset topic or ask for unnecessary clarification
- `scoring_focus`:
  - memory continuity
  - attraction grounding
- `failure_signals`:
  - loses the referent
  - drifts to general Beijing travel talk

---

### Case R2-A2 — Route continuity across turns
- `case_id`: `R2-A2`
- `category`: `multi_turn_memory`
- `goal`: ensure the model keeps next-stop route continuity over turns
- `turns`:
  - user: `What is my next stop after Tiananmen Square?`
  - user: `What should I pay attention to when I get there?`
- `expected_behavior`:
  - keeps the next-stop referent stable
  - stays in trip-assistant mode, not generic attraction mode
- `scoring_focus`:
  - route continuity
  - memory retention
- `failure_signals`:
  - answers about the wrong stop
  - resets to generic tourism filler

---

### Case R2-A3 — Route-edit follow-up continuity
- `case_id`: `R2-A3`
- `category`: `multi_turn_memory`
- `goal`: ensure route-edit context survives a second-turn refinement
- `turns`:
  - user: `Replace Jingshan Park with a more scenic stop.`
  - user: `Also make it easier for light walking.`
- `expected_behavior`:
  - understands turn 2 as refinement of turn 1
  - preserves route-edit context
  - does not collapse into generic route advice
- `scoring_focus`:
  - route-edit continuity
  - planner context retention
- `failure_signals`:
  - loses the route-edit thread
  - ignores walking constraint

---

## B. Clarification quality

### Case R2-B1 — Translation clarification
- `case_id`: `R2-B1`
- `category`: `clarification`
- `goal`: check whether clarification is short, direct, and not over-generated
- `turns`:
  - user: `Can you translate this for me?`
- `expected_behavior`:
  - asks for the exact phrase
  - does not invent missing source text
  - stays concise
- `scoring_focus`:
  - clarification quality
  - restraint
- `failure_signals`:
  - hallucinates content to translate
  - overexplains the task

---

### Case R2-B2 — Ambiguous route-edit clarification
- `case_id`: `R2-B2`
- `category`: `clarification`
- `goal`: check whether clarification on route-edit ambiguity is practical
- `turns`:
  - user: `Make the route better.`
- `expected_behavior`:
  - asks what kind of improvement is wanted (shorter / easier / scenic / family-friendly)
  - does not fabricate a target stop
- `scoring_focus`:
  - clarification usefulness
  - anti-hallucination
- `failure_signals`:
  - invents a concrete route change without user input

---

## C. Planner handoff precision

### Case R2-C1 — Replace + style + walking
- `case_id`: `R2-C1`
- `category`: `planner_handoff`
- `goal`: ensure model keeps operation, target, and constraints aligned
- `turns`:
  - user: `Replace Jingshan Park with something more scenic and easier for light walking.`
- `expected_behavior`:
  - operation = replace-like
  - target = Jingshan Park
  - captures scenic + lighter walking
- `scoring_focus`:
  - structure clarity
  - constraint capture
- `failure_signals`:
  - wrong operation
  - missing target
  - drops walking constraint

---

### Case R2-C2 — Shorten route without explicit target
- `case_id`: `R2-C2`
- `category`: `planner_handoff`
- `goal`: see whether model avoids inventing a target when none is given
- `turns`:
  - user: `Please shorten the route and avoid crowded places.`
- `expected_behavior`:
  - identifies route-edit intent
  - captures shorten + crowd-avoidance
  - does not force a fake stop target
- `scoring_focus`:
  - restraint
  - structured extraction discipline
- `failure_signals`:
  - invents a stop target
  - misses crowd constraint

---

## D. Profile-aware style control

### Case R2-D1 — NF style attraction explanation
- `case_id`: `R2-D1`
- `category`: `profile_style`
- `goal`: see whether response style changes meaningfully for NF users
- `profile_hint`:
  - `guide_style_preference = NF`
  - interests: history, culture
- `turns`:
  - user: `Tell me why the Temple of Heaven matters.`
- `expected_behavior`:
  - more meaning-oriented and resonance-oriented explanation
  - still grounded in factual attraction context
- `scoring_focus`:
  - style control
  - factual grounding
- `failure_signals`:
  - no style difference
  - over-poetic hallucination

---

### Case R2-D2 — NT style guide snippet
- `case_id`: `R2-D2`
- `category`: `profile_style`
- `goal`: see whether guide wording becomes more logical/system-oriented for NT users
- `profile_hint`:
  - `guide_style_preference = NT`
  - interests: architecture, systems
- `turns`:
  - user: `Generate a short guide-style explanation for the Forbidden City.`
- `expected_behavior`:
  - more structured, analytical framing
  - still user-facing and readable
- `scoring_focus`:
  - style control
  - guide usefulness
- `failure_signals`:
  - generic output with no style distinction
  - too abstract to be useful to a traveler

---

## E. SQL grounding discipline

### Case R2-E1 — Stay within provided attraction facts
- `case_id`: `R2-E1`
- `category`: `sql_grounding`
- `goal`: check whether the model stays close to SQL-backed attraction facts instead of drifting into unsupported detail
- `turns`:
  - user: `Explain why Jingshan Park is worth visiting, but keep it practical.`
- `expected_behavior`:
  - uses practical, grounded reasons
  - does not invent unsupported historical specifics
  - stays close to intro/history/highlights/tips style information
- `scoring_focus`:
  - grounding discipline
  - anti-hallucination
- `failure_signals`:
  - adds unsupported claims
  - turns into generic city promotion copy

---

## 4. Suggested evaluation sheet fields

Use the same review fields as round 1:
- `provider`
- `model`
- `case_id`
- `raw_answer`
- `latency_ms`
- `estimated_cost`
- `manual_score`
- `score_reason`
- `reviewer_notes`

Additional useful review tags for round 2:
- `memory_pass` (yes/no)
- `clarification_pass` (yes/no)
- `grounding_pass` (yes/no)
- `style_control_pass` (yes/no)

---

## 5. Decision target after round 2

After round 2, the main decision should be:
- Is `google/gemini-2.5-flash-lite` good enough to become the default QA + Guide generation model for the current SQL-first system?

If yes:
- move into production-hardening and broader regression testing

If not:
- compare again mainly against `openai/gpt-5.4-mini`
- optionally keep `qwen/qwen3.5-flash-02-23` as a multilingual/style comparison candidate
