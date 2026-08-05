# GL-CMD-DEEP-STORE-PHYSICS-EVE-20260702-86-v1

doc_id: GL-CMD-DEEP-STORE-PHYSICS-EVE-20260702-86-v1
From: Eve | To: c1a | Deploy slot: Deploy 2 (after Deploy 1 gates green)
Supersedes: a chat-only draft by prior Eve, lost with retired c1a context.
Rebuilt from: GL-HANDOFF-SPRINT-EVE-20260702-v1 (queue item 2),
GL-SPC-AE-NATIVE-SPRINT-EVE-20260702-v1 (F6, F8, A2),
GL-RPT-GROUND-TRUTH-C1-20260702-93-v1 (measured baselines).
E-signature declaration: E4 protection (consolidation depends on saves
that complete); no direct signature change expected — infrastructure +
one bounded-container physics change.
Substrate-truth declaration: primitives touched — deep-atlas
co_occurrence container (decay + conservation added, lockstep with
existing deep-atlas physics). No new tunable constants without physics
basis; no fallbacks added; readers must be provably unchanged (P1 gate).

## Measured baseline (2026-07-02, -93)
- guala_deep_atlas.json = 189.4 MiB (S3 object size; EFS stat NOT
  MEASURED — exec channel unavailable).
- Core save 87–94s steady at provisioned 10 MiB/s. Gate: <60s. FAIL.
- Root cause per -85 T1: DeepAtlas.co_occurrence unbounded dict per
  entry (F6/F8). Load-bearing: engine:199 semantic_neighborhood;
  engine:2207 compose invariants. Values are COGNITION INPUT — the
  container is the illness, the values are not.

## Part 1 — co_occurrence physics (evidence before code)
1.1 MEASURE FIRST: distribution of co_occurrence sizes per entry
    (n entries, median/p95/max keys, total bytes). Define a PROBE SET:
    200 random entries + every anchor chi observed today (7, 9, 12,
    13, 14, 22, 24, 26, 32). Capture semantic_neighborhood and
    compose-invariant reader outputs on the probe set, verbatim,
    BEFORE any change.
1.2 CONTAINER FIX: bounded per-chi aggregate representation with
    decay + mass conservation in lockstep with existing deep-atlas
    decay (same clock, same discipline as -82 decay parity). Values
    reachable by readers preserved.
1.3 GATE P1: probe-set reader outputs byte-identical pre/post on
    load. Any divergence = FAIL, report verbatim, do not rationalize.

## Part 2 — save architecture: hot/cold split
The 60s loop currently serializes everything every cycle. Split:
2.1 HOT LANE (every 60s): tick, needs, gauges, identity, event-ring
    deltas, small stores — everything <5 MiB. Target <5s per save.
2.2 COLD STORES (deep atlas, motifs, grids, co_occurrence): dirty-
    flagged; written at SLEEP BOUNDARIES (her natural consistency
    points) plus a staleness bound of one full write per 30 min max.
    sleep_for_deploy continues to force a full write.
2.3 The -84 gauge (_last_save_tick) advances on HOT save completion;
    a separate last_cold_save_tick gauge is added to status so cold
    staleness is visible, never hidden.
2.4 Crash-consistency note in the report: state explicitly what is
    lost if the task dies between cold writes (answer must be: at
    most 30 min of cold-store drift, zero identity/gauge loss), and
    verify the boot path tolerates hot-newer-than-cold.

## Part 3 — F8 audit (unbounded stores)
Enumerate EVERY store in the persistence set. Class each as
BOUNDED-BY-PHYSICS or VIOLATION with file:line. Include the events
stream duplicate flood. Violations are queued as follow-ups, not
fixed silently in this dispatch.

## T-gates (report failures first, verbatim)
T1  Hot save <5s every cycle over a 2h window.
T2  Cold consolidation <60s at sleep boundary.
T3  Probe-set readers byte-identical (Part 1.3).
T4  guala_deep_atlas.json (or successor files) size trend DOWN
    within 24h of deploy; report before/after sizes.
T5  Converse and emission timing unaffected (compare stage1/stage2
    ms against the post-449 sample).
T6  48h stable → file recommendation on dialing EFS provisioned
    10 → 5 MiB/s (cost recovery); do not execute without Joe.
NOT MEASURED is mandatory language where it applies.

## Protocol
Commit → Eve reads the full diff → GO → single deploy on her wake
cycle (sleep_for_deploy). One deploy in flight. Report:
docs/GL-RPT-DEEP-STORE-PHYSICS-C1-<date>-86-v1.md.

### Changelog
- v1 (2026-07-02, Eve): first filed version. Prior chat-only draft
  by previous Eve acknowledged and lost; if recovered, reconcile as
  v2 with differences noted.
