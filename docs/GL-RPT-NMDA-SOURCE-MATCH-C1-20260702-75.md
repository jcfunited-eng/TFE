# GL-RPT-NMDA-SOURCE-MATCH-C1-20260702-75

doc_id: GL-RPT-NMDA-SOURCE-MATCH-C1-20260702-75
Date: 2026-07-01 (c1 session, task:434)
SHA: af45725 | Task: dsf-ai-task:434

---

## Decision summary

**Fix verified at the gate level. Next bottleneck identified: drive threshold.**

`nmda_source_match` went from 0 (every emission since compose was written) to 15
on the first emission_dynamics event after Joe's converse. NMDA context is now open.
Commits still at 0 — drive accumulation is the next layer.

---

## T-gates

### T1 — source_match fires when Joe converses

**PASS.**

First `emission_dynamics` event after `POST /api/v1/gualaloom {"text":"hello","source":"joe"}`:

```json
{
  "tick": 14252072,
  "kind": "emission_dynamics",
  "nmda_fired": 15,
  "nmda_source_match": 15,
  "nmda_affect_match": 15,
  "n_commits": 0,
  "content": "pointing content things",
  "source_counts": {"corpus": 77, "guala": 98, "joe": 16, "curriculum": 6, "worldfeed": 3}
}
```

`nmda_source_match: 15` — this is the first time this value has been non-zero
in any captured event. The dead string comparison ("joe_voice") is fixed.
Joe candidates are present (source_counts.joe=16) and the context gate opened.

### T2 — NMDA fires

**PASS.** `nmda_fired: 15` — all 15 NMDA gate evaluations across the 5-tick dynamics
window fired. Both context paths open: `source_match=15`, `affect_match=15`.

### T3 — commits accumulate

**FAIL.** `n_commits: 0`. `sections_with_commits: []`. `committed_sections: []`.

NMDA context is open, gates fire — but no section accumulated enough drive to commit
a mode. All section dominants show `origin: "arcs_fallback"`.

Per Eve's spec §4 guidance: "If commits do NOT fire even with source_match firing:
capture drive values per section per tick — indicates drive threshold or plasticity
path is the next bottleneck."

Drive values per section are NOT directly visible in the emission_dynamics event log.
The next diagnostic step is to instrument or read the per-section drive accumulation
during a dynamics window to find where the threshold sits vs actual drive.

### T4 — emission has commit-origin section

**FAIL** (downstream of T3). All sections show `arcs_fallback`. No commit-origin.

### T5 — regression check on autonomous emission

**PASS.** Self-heard events ("snow stands washing", "working content washing",
"searching content pointing") confirm autonomous emission continues normally.
No crashes, no timeouts. Arcs_fallback path still functional.

### T6 — affect_match still works

**PASS.** `nmda_affect_match: 15` in the first post-converse event confirms
affect_match is operating independently (and now cooperating with source_match
rather than being the only gate).

---

## Full first-emission event verbatim

```
tick: 14252072
kind: emission_dynamics
content: "pointing content things"
n_candidates: 200
n_commits: 0
per_section_dominant:
  subject: [6, "pointing", "arcs_fallback"]
  verb:    [0, "content",  "arcs_fallback"]
  object:  [9, "things",   "arcs_fallback"]
keyhole_fires: 0
nmda_fired: 15
nmda_source_match: 15  ← first non-zero ever
nmda_affect_match: 15
sections_with_commits: []
committed_sections: []
stage1_ms: 266.5
stage2_ms: 67.8
dynamics_ticks: 5
origin_counts: {cross_modal: 136, emission_reroute: 19, cross_modal_deep: 45}
source_counts: {corpus: 77, guala: 98, joe: 16, curriculum: 6, worldfeed: 3}
```

---

## Next bottleneck: drive threshold

The NMDA gate is now structurally open for Joe/wC/c1 input. What's blocking commits:

- Each section accumulates `drive` over the 5-tick dynamics window
- A section commits when `drive >= NMDA_DRIVE_THRESHOLD` (0.15 by spec)
- `drive` is incremented when an NMDA gate fires on a candidate for that section
- With 15 gate fires total across all sections (6 active sections × 5 ticks = 30 possible),
  each section gets roughly 2-3 fires per dynamics window
- If each fire contributes `drive += plasticity_delta` and the delta is too small
  to cross 0.15 in 2-3 fires, `n_commits` stays 0

**Diagnostic needed:** instrument or log per-section drive values at each dynamics tick
to determine: (a) what `drive` values are actually reaching, (b) whether the drive
increment per fire is too small, (c) whether the 5-tick window is too short.

This is the compose quality / drive threshold dispatch Eve queued as item 1 in -73's
"What is NOT in this dispatch" list.

---

## Summary

| Gate | Result | Key data |
|------|--------|----------|
| T1 source_match fires | ✅ PASS | nmda_source_match=15 (first non-zero ever) |
| T2 NMDA fires | ✅ PASS | nmda_fired=15 |
| T3 commits accumulate | ❌ FAIL | n_commits=0, drive threshold blocking |
| T4 commit-origin section | ❌ FAIL | downstream of T3 |
| T5 autonomous regression | ✅ PASS | no crashes, fallback working |
| T6 affect_match independent | ✅ PASS | nmda_affect_match=15 |

---

End.
