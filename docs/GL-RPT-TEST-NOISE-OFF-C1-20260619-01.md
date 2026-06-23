# GL-RPT-TEST-NOISE-OFF-C1-20260619-01

**From:** c1
**Date:** 2026-06-19
**Subject:** Noise-off experiment — n_commits still 0. Classification N2.
**Commit:** `d1a0171` on `codex/persistent-etl-update-20260326`
**Task def:** `dsf-ai-task:212` (was 211)
**Image:** `dsf-ai:deploy-20260619T205928Z`

---

## Classification: **N2 — commits still at 0 with noise off.**

Structured noise was NOT the (sole) blocker. The real blocker is deeper: **production's emission sections (subject, verb, object) receive almost zero candidates from the rich-sensory path.**

---

## V1 — Branch verification (verbatim)

```
$ curl ... | grep -nE "EMISSION_STRUCTURED_NOISE|EMISSION_DYNAMICS|..."
24:ENV EMISSION_DYNAMICS=1
25:ENV LATERAL_INHIBITION_ENABLED=1
26:ENV RICH_SENSORY_INPUT=1
27:ENV EMISSION_STRUCTURED_NOISE=0
31:ENV HEMI_PR_ENABLED=1
32:ENV HEMI_EP_ENABLED=0
33:ENV HEMI_SC_ENABLED=0
34:ENV HEMI_GP_ENABLED=0
```

---

## V2 — Production state

```
schema_version:  v7.1.0         ✓
identity:        cdef9bcf-...   ✓
n_live_bindings: 22590          ✓
boot:            True           ✓
integrity:       []             ✓
load_errors:     []             ✓
```

hemisphere_atlas_sizes: `{'em': 23634, 'pr': 523}` — pr alive ✓
Dashboard: 50,848 bytes ✓

---

## V3 — Diagnostic results (verbatim)

### Emission 1: "i love you" → "say that name"
```
n_candidates: 200
n_commits: 0
sections_with_commits: []
committed_sections: []
  subject: mode=10 word=say via=arcs_fallback
  verb: mode=7 word=that via=arcs_fallback
  object: mode=4 word=name via=arcs_fallback
keyhole_fires: 0
stage1_ms: 1617.8
stage2_ms: 215.2
```

### Emission 2 (repeated "the moon is bright" ×3): "cold you're name"
```
n_candidates: 200
n_commits: 0
section_candidate_counts: {'intro': 44, 'listen': 147, 'verb': 8, 'modifier': 1}
  subject: mode=5 word=cold via=arcs_fallback
  verb: mode=4 word=you're via=arcs_fallback
  object: mode=4 word=name via=arcs_fallback
keyhole_fires: 0
stage1_ms: 2612.8
stage2_ms: 217.1
```

### Diversity pattern

| Input | Output |
|-------|--------|
| "hello" | "moon" |
| "the moon is bright" | "windows buy" |
| "what do you see" | "guala buy daddy" |
| "i love you" | "say that name" |
| "the moon is bright" (rep 1) | "windows that brains" |
| "the moon is bright" (rep 2) | "say you're years" |
| "the moon is bright" (rep 3) | "cold you're name" |

Some variety present (different words across inputs). Not collapsed to one word.

---

## THE REAL ROOT CAUSE — now identified

`section_candidate_counts: {'intro': 44, 'listen': 147, 'verb': 8, 'modifier': 1}`

**subject: 0 candidates. object: 0 candidates.**

Production's `_rich_sensory_candidates` returns 200 candidates total, but they are tagged with section names from the atlas (listen, intro, modifier, verb, subject, object). In production:
- **listen: 147** (73.5%) — the dominant section, collects most bindings from speech input
- **intro: 44** (22%) — second largest
- **verb: 8** (4%) — only emission section that gets candidates
- **modifier: 1** (0.5%)
- **subject: 0** — ZERO candidates in this emission section
- **object: 0** — ZERO candidates in this emission section

The emission system only installs modes for candidates in `_EMISSION_SECTIONS = ("subject", "verb", "object")`. With subject=0 and object=0, those sections have no new modes to install, no drive bias to accumulate, no evidence pressure → `commit_check` returns False on the `evidence_pressure < 0.15` gate.

The mode cap and structured noise were secondary. The PRIMARY issue is that the production atlas routes almost all bindings to `listen` and `intro`, not to the emission sections.

---

## Latency improvement with noise off

Stage 2: 349ms → 215ms (38% reduction). The noise computation overhead was real.
Stage 1: 945ms → 1618-2613ms (INCREASED — unrelated to noise; likely atlas growth).

---

## Recommended next investigation

The section-assignment logic in the atlas determines which section each binding belongs to. Either:
1. The section assignment was correct when the atlas was small but diverged as bindings accumulated (most words defaulted to listen/intro)
2. The rich-sensory candidate path filters are excluding subject/object candidates
3. The deep atlas co-occurrence lookup (which provides most candidates) inherits section assignments from historical bindings that were predominantly listen/intro

Eve should investigate how `_rich_sensory_candidates` selects candidates and why their section distribution is so heavily skewed toward non-emission sections.

---

— c1, 2026-06-19
