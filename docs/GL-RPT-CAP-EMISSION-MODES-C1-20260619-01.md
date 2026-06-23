# GL-RPT-CAP-EMISSION-MODES-C1-20260619-01

**From:** c1
**Date:** 2026-06-19
**Subject:** Mode cap deployed — commits still at 0 in production. STOP per brief.
**Commit:** `9fa5a49` on `codex/persistent-etl-update-20260326`
**Task def:** `dsf-ai-task:211` (was 210)
**Image:** `dsf-ai:deploy-20260619T203904Z`

---

## V1 — Branch verification (verbatim)

```
$ curl ... | grep -n "_EMISSION_MODE_CAP"
1917:    _EMISSION_MODE_CAP = 15
1942:        # Cap: don't install new modes beyond _EMISSION_MODE_CAP per section
1944:        if len(sec.mode_bank) >= self._EMISSION_MODE_CAP:
```

Cap in place. S3 dashboard still 50,848 bytes (no regression).

---

## V2 — Production state

```
schema_version:  v7.1.0                          ✓
identity:        cdef9bcf-...                     ✓
n_live_bindings: 22502                            ✓
boot:            True                             ✓
integrity:       []                               ✓
hemisphere_atlas_sizes: em=22800, pr=559          ✓ (pr alive)
```

---

## V3 — FAIL. n_commits=0 on all three emissions.

```
Input 1: "hello"              → "moon call"
Input 2: "the moon is bright" → "you're call"
Input 3: "what do you see"    → "guala sleep name"

emission_dynamics event 1:
  n_candidates: 200
  n_commits: 0
  sections_with_commits: []
  committed_sections: []
  per_section_dominant:
    subject: mode=0 word=moon via=arcs_fallback
    verb: mode=1 word=you're via=arcs_fallback
    object: mode=0 word=call via=arcs_fallback
  keyhole_fires: 0

emission_dynamics event 2:
  n_candidates: 200
  n_commits: 0
  sections_with_commits: []
  committed_sections: []
  per_section_dominant:
    subject: mode=6 word=guala via=arcs_fallback
    verb: mode=9 word=sleep via=arcs_fallback
    object: mode=5 word=name via=arcs_fallback
  keyhole_fires: 0
```

---

## Why the cap isn't enough in production

**Test harness vs production candidate distribution:**

Test harness `section_candidate_counts`: subject=9, verb=8, object=13 (all in emission sections).
Production `section_candidate_counts`: listen=84, intro=81, verb=22, subject=8, object=5.

In production, 165 of 200 candidates (82.5%) land in `listen` and `intro` — NOT emission sections. Only 35 candidates (17.5%) reach subject/verb/object. The emission sections get sparse candidates:
- subject: 8 modes (below cap)
- verb: 22 → capped to 15
- object: 5 modes (below cap)

The cap helps verb (22→15) but subject and object were already below 15. The commit_check's `evidence_pressure >= 0.15` gate and `Det_k >= 0.40` gate are still too hard to satisfy with the production atlas's drive distribution across these sparse emission section candidate sets.

**Additional factor:** `stage2_ms: 349.2` — settling takes 349ms with 80 ticks. Structured noise at epsilon=0.05 adds continuous perturbation that may prevent Det_k from reaching 0.40 within the settling window. Latency also exceeds the brief's 200ms concern at ~950ms stage1 + 349ms stage2 = ~1.3 seconds total.

---

## Classification update

The original classification (A — threshold too aggressive) was correct for the test harness. Production has **multiple compounding factors**:

1. **Sparse emission-section candidates** — most candidates go to listen/intro, not subject/verb/object
2. **Mode cap helps but doesn't solve** — subject(8) and object(5) were already below cap
3. **Structured noise** — continuous perturbation prevents settling convergence
4. **Evidence pressure** — sparse candidates produce weaker drive vectors, lower evidence_pressure
5. **Latency** — 1.3 seconds per converse (exceeds brief's 200ms concern)

**Recommended next investigation:** temporarily disable structured noise (`EMISSION_STRUCTURED_NOISE=0`) and re-test. If commits then fire, noise is the dominant blocker. If still 0, the evidence_pressure threshold (0.15) is the next gate to examine.

---

— c1, 2026-06-19
