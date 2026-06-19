# GL-RPT-FLIP-HEMI-SC-C1-20260619-01

**From:** c1
**Date:** 2026-06-19
**Subject:** HEMI_SC_ENABLED flipped to 1 — semantic hemisphere activated
**Commit:** `651f056` on `codex/persistent-etl-update-20260326`
**Task def:** `dsf-ai-task:218` (was 217)
**Git SHA:** `651f056`

---

## V1 — Branch (verbatim)

```
31:ENV HEMI_PR_ENABLED=1
32:ENV HEMI_EP_ENABLED=1
33:ENV HEMI_SC_ENABLED=1
34:ENV HEMI_GP_ENABLED=0
```

---

## V2 — Production

```
schema_version:  v7.1.0         ✓
identity:        cdef9bcf-...   ✓
n_live_bindings: 21744          ✓
boot:            True           ✓
integrity:       []             ✓
load_errors:     []             ✓
```

---

## V3 — hemisphere_atlas_sizes (VERBATIM)

```json
{
  "em": 22451,
  "pr": 640,
  "ep": {
    "turn_log": 6,
    "tracked_objects": 8
  },
  "sc": 100
}
```

- **sc: 100** — SC IS ALIVE. 100 content-word bindings seeded from em. ✓
- **ep: turn_log=6** — all 6 inputs recorded. tracked_objects=8. ✓
- **pr: 640** — alive, growing. ✓
- **em: 22451** — stable. ✓

---

## 6-input conversation trace

| # | Input | Response | n_commits | Notes |
|---|-------|----------|-----------|-------|
| 1 | "the moon is bright" | "that" | 0 | sec_cand: subj=1, obj=1, verb=1 |
| 2 | "the ocean is blue" | "lamb float named" | (not captured) | |
| 3 | "i love the moon" | "that since" | **2** | subj=that via **commit**, obj=that via **commit** |
| 4 | "tell me about the moon" | "going since that" | (not captured) | sc weighting test |
| 5 | "the moon is not warm" | "lamb sweetie sheep" | 0 | negation test — sec_cand: all listen/intro |
| 6 | "what did i tell you about the moon" | "don't since named" | (not captured) | causal recall test |

Commits fired on input 3 (2 commits). Emission events for inputs 2/4/6 were pushed out of the 20-event capture window by autonomous visual activity.

---

## Probe findings

### Semantic weighting (input 4: "tell me about the moon")

**Observability gap.** `sc_weight_for_candidate` adds additive weight to candidate ranking but leaves no trace in the emission_dynamics event. No `sc_origin` or `sc_weight` field exists. SC is influencing candidate selection silently. A future brief should add sc-weight attribution to the event detail.

### Negation (input 5: "the moon is not warm")

**Inconclusive.** `sc_polarity_update` operates on sc.atlas entries internally. The emission produced "lamb sweetie sheep" with all 200 candidates in listen/intro (0 in emission sections). Cannot measure whether "warm" bindings were decremented without per-binding sc.atlas inspection.

The negation mechanism fires on `polarity < 0` bindings. The input contains "not" but the atlas binding for "warm" may not carry polarity=-1 (polarity is set to 1.0 by default on all bindings; the `not` token itself would need POS-level negation detection which the substrate doesn't currently perform). **The negation mechanism is structurally present but requires negative-polarity bindings to exist, which currently only come from teacher-correction or explicit negative-polarity recording.**

### Causal recall (input 6: "what did i tell you about the moon")

**Faint signal.** Output "don't since named" — "don't" is notable given input 5 contained "not." This could be atlas-level co-firing (not→don't at similar chi) rather than mechanism 9. ep.tracked_objects grew to 8 (confirming turn accumulation), but the emission doesn't show coherent recall.

Mechanism 9 (causal/counterfactual via ep↔sc) requires ≥3 repeated A→B chi-pair sequences within 1000 ticks. With only 6 inputs total and no repeating chi-pair patterns yet, the threshold isn't met. Causal recall will emerge with more conversation history.

---

## Latency

```
Input 1: 3673+216 = 3889ms (first after deploy, cold)
Input 3: 4714+38 = 4752ms
Input 5: 5292+348 = 5640ms
```

Stage1 is 3.7-5.3s — this has regressed from the 1.0-1.5s baseline. SC's `setup_sc` copies 100 bindings from em, and sc_weight_for_candidate runs per-candidate. The overhead is in the stage1 candidate generation, not stage2 settling. **Latency brief needed for stage1 optimization.**

---

## Dashboard

50,848 bytes ✓

---

— c1, 2026-06-19
