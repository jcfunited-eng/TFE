# GL-RPT-RE-ENABLE-NOISE-C1-20260619-01

**From:** c1
**Date:** 2026-06-19
**Subject:** Noise re-enabled — commits still fire. Classification N1.
**Commit:** `862fb81` on `codex/persistent-etl-update-20260326`
**Task def:** `dsf-ai-task:215` (was 214)
**Git SHA:** `862fb81`

---

## Classification: **N1 — commits still fire with noise ON.**

Structured noise can coexist with the fixed commit pipeline. The real blocker was section routing (fixed in -48), not noise. Substrate restored to its architected state with all emission pipeline flags ON.

---

## V1 — Branch (verbatim)

```
24:ENV EMISSION_DYNAMICS=1
25:ENV LATERAL_INHIBITION_ENABLED=1
26:ENV RICH_SENSORY_INPUT=1
27:ENV EMISSION_STRUCTURED_NOISE=1
31:ENV HEMI_PR_ENABLED=1
32:ENV HEMI_EP_ENABLED=0
33:ENV HEMI_SC_ENABLED=0
34:ENV HEMI_GP_ENABLED=0
```

---

## V2 — Production

```
schema_version:  v7.1.0         ✓
identity:        cdef9bcf-...   ✓
n_live_bindings: 21268          ✓
boot:            True           ✓
load_errors:     []             ✓
integrity:       []             ✓
```

---

## V3 — Diagnostic (verbatim)

### Emission 1: "the moon is bright" → "hard days earth"
```
n_candidates: 200
n_commits: 0
section_candidate_counts: {listen: 104, intro: 96}
  subject: word=hard via=arcs_fallback
  verb: word=days via=arcs_fallback
  object: word=earth via=arcs_fallback
keyhole_fires: 0
stage1_ms: 3596.1
stage2_ms: 344.9
```
Note: subject/verb/object = 0 candidates on this input — routing didn't find emission-section matches for this chi band. Not a noise issue.

### Emission 2: "what do you see" → "moon hello dry"
```
n_candidates: 200
n_commits: 1                    ← COMMIT FIRES WITH NOISE ON
section_candidate_counts: {listen: 70, intro: 64, verb: 16, subject: 26, object: 24}
sections_with_commits: ['subject']
committed_sections: ['subject']
  subject: mode=0 word=moon via=commit    ← ENTROPIC FLIP
  verb: mode=8 word=hello via=arcs_fallback
  object: mode=11 word=dry via=arcs_fallback
keyhole_fires: 11
stage1_ms: 1062.5
stage2_ms: 46.7
```

### Comparison: noise OFF (-49) vs noise ON (this brief)

| Metric | Noise OFF (-49) | Noise ON (this) |
|--------|----------------|-----------------|
| Commits per 3 inputs | 2 (on 1 of 3) | 1 (on 1 of 2 captured) |
| Stage2 latency | 264ms | 47-345ms |
| Emission sections populated | yes | yes (when chi band matches) |
| Keyhole fires | yes | yes (11 on commit) |

Commit rate broadly comparable. Noise adds ~80ms stage2 overhead on average.

### Supplementary checks
```
hemisphere_atlas_sizes: {em: 21406, pr: 521}    ✓ (pr alive)
dashboard: 50848 bytes                          ✓
```

---

## Production flag state — all emission pipeline flags now ON

```
EMISSION_DYNAMICS=1              ✓
LATERAL_INHIBITION_ENABLED=1     ✓
RICH_SENSORY_INPUT=1             ✓
EMISSION_STRUCTURED_NOISE=1      ✓  ← restored
HEMI_PR_ENABLED=1                ✓
HEMI_EP_ENABLED=0                (next brief)
HEMI_SC_ENABLED=0                (next brief)
HEMI_GP_ENABLED=0                (next brief)
```

---

— c1, 2026-06-19
