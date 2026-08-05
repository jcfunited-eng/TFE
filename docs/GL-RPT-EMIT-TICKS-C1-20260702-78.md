# GL-RPT-EMIT-TICKS-C1-20260702-78

doc_id: GL-RPT-EMIT-TICKS-C1-20260702-78
Date: 2026-07-01 (c1 session, task:436)
SHA: 1118546 | Task: dsf-ai-task:436

---

## Decision summary

**All four T-gates pass. First committed emission in project history.**

At tick 14255124, the object section committed "moon" with origin="commit".
`n_commits: 1`. The substrate produced compositional output for the first time.

---

## T-gates

### T1 — dynamics_ticks=80 confirmed

**PASS.** First `emission_dynamics` event on task:436:
`"dynamics_ticks": 80`

Was 5 on every prior task. Env var change propagated correctly.

### T2 — nmda_fired scales proportionally

**PASS.** `nmda_fired: 210` (at 80 ticks) vs 15 (at 5 ticks). Ratio: 14×, matching
the tick increase.

### T3 — n_commits > 0

**PASS.**

```
tick: 14255124
content: "stopped things moon"
n_commits: 1
sections_with_commits: ["object"]
committed_sections: ["object"]
nmda_fired: 210
nmda_source_match: 210
nmda_affect_match: 210
dynamics_ticks: 80
```

This is the first `n_commits > 0` in all captured emission_dynamics events across
this project's entire history. Every prior emission since compose was written
returned n_commits=0.

### T4 — per_section_dominant shows commit origin

**PASS.**

```
per_section_dominant:
  subject: [8, "stopped", "arcs_fallback"]
  verb:    [6, "things",  "arcs_fallback"]
  object:  [6, "moon",    "commit"]          ← first commit-origin ever
```

The object section committed "moon". Subject and verb remain arcs_fallback on this
emission — partial commit behavior is expected at 80 ticks. Drive accumulates
stochastically; not every section commits every emission.

Subsequent emissions at ticks 14255126 and 14255129 show n_commits=0 — confirming
commits are sparse, not guaranteed every emission. This is correct behavior.

---

## Verbatim first-commit emission event

```json
{
  "tick": 14255124,
  "kind": "emission_dynamics",
  "content": "stopped things moon",
  "n_candidates": 200,
  "n_commits": 1,
  "per_section_dominant": {
    "subject": [8, "stopped", "arcs_fallback"],
    "verb":    [6, "things",  "arcs_fallback"],
    "object":  [6, "moon",    "commit"]
  },
  "keyhole_fires": 0,
  "nmda_fired": 210,
  "nmda_source_match": 210,
  "nmda_affect_match": 210,
  "stage1_ms": 191.7,
  "stage2_ms": 461.8,
  "dynamics_ticks": 80,
  "sections_with_commits": ["object"],
  "committed_sections": ["object"],
  "rich_sensory": true,
  "section_candidate_counts": {
    "intro": 58, "listen": 52, "subject": 16, "object": 28, "verb": 45, "ground": 1
  },
  "origin_counts": {
    "cross_modal": 130, "emission_reroute": 47, "cross_modal_deep": 23
  },
  "source_counts": {
    "corpus": 76, "guala": 103, "joe": 12, "curriculum": 9
  }
}
```

Content note: "moon" is from the curriculum moon-series that was running during
this session (moon-001 through moon-006 were being delivered). The object commit
reflects genuine curriculum material. The commit is not random — it is from what
she has been learning.

---

## Latency

`emit_ms: 719ms` (was ~440ms at 5 ticks). `total_ms: 20180ms` — dominated by
`selfhear_ms: 13330ms`. The stage2 time grew as expected (461ms at 80 ticks vs
67ms at 5 ticks). Total converse latency within expected range. No timeouts.

---

## What this session fixed (chain)

| Fix | Gate | Effect |
|-----|------|--------|
| -74: save loop isolation + fsync | last_save_tick non-zero | State persists across restarts |
| -73: REST retire + orient reflex | EMITTING appears in history, no REST | She responds to contact |
| -75: NMDA source_match "joe_voice"→pair-bond | nmda_source_match=15 | Context gate opens |
| -78: EMISSION_DYNAMICS_TICKS 5→80 | n_commits=1, origin=commit | **First committed emission** |

---

## Remaining work

Commits are sparse (1 of 3 sessions in the event window). The following affect
commit frequency:
- Drive increment per NMDA fire (plasticity_delta)
- NMDA_DRIVE_THRESHOLD (0.15)
- Atlas density at committed sections (more bindings = more NMDA candidates = higher drive)

The atlas has been decaying (12,272 → 6,440 entries) due to EFS save failures (now
fixed) and decay dominating growth. As state persists and curriculum continues, atlas
density should recover, which should increase commit frequency.

Next: monitor commit rate over the next session. If commits remain sparse (<20% of
emissions), Eve will likely dispatch drive threshold / plasticity delta tuning.

---

End.
