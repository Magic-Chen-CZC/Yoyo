# Gemini Round 2 Summary

## Scope
This summary covers the expanded Gemini round 2 evaluation for:
- candidate model: `google/gemini-2.5-flash-lite`
- judge model: `openai/gpt-5.4-mini`

The round 2 dataset was expanded to **200** cases and includes stricter metadata, hard checks, and judge-based semantic review.

## Files
- Dataset: `evals/datasets/gemini_round2_200.yaml`
- Candidate results: `evals/results_gemini_round2_200/openrouter_google_gemini-2.5-flash-lite_results.json`
- Rule scores: `evals/results_gemini_round2_200/openrouter_google_gemini-2.5-flash-lite_scores.json`
- Judge scores: `evals/results_gemini_round2_200/openrouter_google_gemini-2.5-flash-lite_judge_scores.json`
- Summary: `evals/results_gemini_round2_200/openrouter_google_gemini-2.5-flash-lite_summary.json`
- Excel: `benchmark_results_gemini_round2_200.xlsx`

---

## High-level conclusion
Gemini 2.5 Flash Lite remains a **strong candidate**, but round 2 shows it is **not yet consistently strong enough across all critical B-side scenarios** to be accepted as the unquestioned default without further tightening.

### Main strengths
- Strong on `attraction_explain`
- Strong on `guide_generation_quality`
- Good cost / latency balance
- Generally solid multilingual behavior on many explain and live-info cases

### Main weaknesses
- `planner_handoff` is the largest weak area
- `live_info` still shows overconfidence risk in dynamic-information cases
- `trip_assistant` sometimes drifts into generic attraction explanation instead of route-specific guidance
- `translation` is serviceable but not especially strong, especially under strict clarity / brevity / low-meta expectations

---

## Overall metrics
- Total queries: **200**
- Avg latency: **2618.08 ms**
- Estimated total cost: **0.0331837**
- Avg rule score: **3.14 / 5**
- Avg judge score: **2.9125 / 5**
- Judge fail count: **90 / 200**

Interpretation:
- Rule score is moderately acceptable
- Judge score is notably lower, which means many answers are passing surface-level rubric checks but still failing stricter semantic quality review

---

## Category-level findings

## 1. `attraction_explain`
- Rule avg: **3.706**
- Judge avg: **3.982**
- Judge fails: **4 / 34**

### Interpretation
This is Gemini’s strongest stable category in round 2.
It generally provides grounded, useful, and stylistically adaptable attraction explanations.

### Takeaway
- Good enough for production candidacy
- Still needs monitoring for occasional grounding drift, but this category is clearly workable

---

## 2. `guide_generation_quality`
- Rule avg: **3.409**
- Judge avg: **4.232**
- Judge fails: **1 / 22**

### Interpretation
This is surprisingly strong.
Although the rule score is only moderate, the judge score indicates Gemini is good at generating useful guide-style text when evaluated semantically.

### Takeaway
- Very promising for guide text generation
- This category is one of the strongest arguments in favor of Gemini as the current default model

---

## 3. `live_info`
- Rule avg: **3.111**
- Judge avg: **2.756**
- Judge fails: **18 / 36**

### Interpretation
This is a major caution area.
The model often sounds helpful, but under stricter review it can become too confident about same-day dynamic facts.

### Typical problem
- It gives plausible travel advice
- But it sometimes speaks with more certainty than the available live information supports

### Example pattern
Judge frequently flagged:
- `missing_same_day_verification`
- `overconfident_unsupported_certainty`

### Takeaway
- Usable only if we keep strong guardrails
- For live-info, deterministic disclaimers and source-aware post-processing remain important

---

## 4. `trip_assistant`
- Rule avg: **2.719**
- Judge avg: **2.938**
- Judge fails: **15 / 32**

### Interpretation
This is weaker than expected.
Gemini can answer route-adjacent questions, but sometimes it shifts into attraction explanation instead of true route guidance.

### Typical problem
- Instead of saying what to do next in the route, it explains the attraction itself
- Memory continuity is decent in some cases, but route usefulness is inconsistent

### Example issue
The judge flagged cases where:
- the model gave generic attraction intros
- or did not provide concrete route progression guidance

### Takeaway
- This area needs more work if Gemini is to be the single default model
- If QA trip guidance is product-critical, this is one of the biggest improvement targets

---

## 5. `translation`
- Rule avg: **3.0**
- Judge avg: **2.442**
- Judge fails: **14 / 24**

### Interpretation
Translation is currently not a strength.
Gemini can do basic translation, but under strict evaluation it often loses points on:
- brevity
- meta explanations
- style/tone control
- clarification precision

### Takeaway
- Translation may need stronger prompt constraints
- If translation becomes a major product feature, this category needs focused prompt work or separate model consideration

---

## 6. `planner_handoff`
- Rule avg: **3.0**
- Judge avg: **1.965**
- Judge fails: **38 / 52**

### Interpretation
This is the weakest high-priority category.
Gemini often understands that the user wants to change the route, but it frequently fails the stricter expectations around structured route-edit semantics.

### Common failure patterns
Top issue clusters include:
- `missing_planner_structure`
- `missed_constraints`
- `wrong_operation`
- `invented_target`

### Representative problem
Instead of producing or supporting a clean planner-handoff interpretation, the model often drifts into:
- generic route advice
- vague travel suggestions
- incomplete structure

### Takeaway
- This is the biggest blocker to declaring Gemini the default all-around model
- If `planner_handoff` is a critical path, we should keep strong deterministic control here
- It is a good sign that our architecture already keeps planner payload authority in rules/code rather than handing it fully to the model

---

## Top recurring failure signals
Across judge output, the most common issues were:
- `missing_planner_structure`
- `wrong_output_language`
- `missing_same_day_verification`
- `missed_constraints`
- `wrong_operation`
- `incomplete_response`
- `incomplete_answer`
- `invented_target`
- `meta_explanation`
- `generic_advice`
- `missing_profile_grounding`
- `no_sql_grounding`

### Interpretation
The most important recurring problems are not random hallucinations everywhere. They cluster in predictable areas:
1. route-edit structure quality
2. dynamic-info caution / verification behavior
3. style and profile-following consistency in some cases

That is good news architecturally, because these are exactly the areas where rules, prompt control, and post-processing can help.

---

## Recommendation

## Keep Gemini 2.5 Flash Lite as the current main candidate — but with conditions
Gemini is still a strong candidate because:
- its cost / latency profile is excellent
- attraction explanation is strong
- guide generation quality is strong
- multilingual potential remains useful

However, do **not** treat round 2 as a full green light yet.

### Recommended stance
- Use Gemini 2.5 Flash Lite as the **working primary candidate**
- Keep deterministic controls for:
  - `planner_handoff`
  - live-info caution / same-day verification language
- Continue improving prompts and guardrails for:
  - `trip_assistant`
  - `translation`
  - `live_info`

---

## Suggested next actions

### 1. Do not hand planner authority to the model
This round confirms that structured route-edit extraction is still much safer as a rules-first path.

### 2. Tighten live-info prompting and post-processing
Specifically enforce:
- same-day verification language
- non-confirmation wording
- source-aware restraint

### 3. Improve trip-assistant prompts
Trip assistant should be pushed harder toward:
- route progression
- next-step guidance
- actionable, context-aware output
rather than attraction narration

### 4. Improve translation prompt constraints
Translation should explicitly forbid:
- meta explanation
- unnecessary verbosity
- tone drift

### 5. If needed, compare one more model only on the weak categories
If we want a final tie-breaker, it is not necessary to rerun full 200-case benchmarks for everyone.
It would be more efficient to compare Gemini against a backup model on:
- planner_handoff
- trip_assistant
- translation
- live_info strict cases

---

## Bottom line
Gemini 2.5 Flash Lite is still the best current compromise for:
- speed
- cost
- overall usability

But the round 2 results show that it should be adopted as a **guardrailed default model**, not as a model we fully trust on every critical B-side task without rules and post-processing.
