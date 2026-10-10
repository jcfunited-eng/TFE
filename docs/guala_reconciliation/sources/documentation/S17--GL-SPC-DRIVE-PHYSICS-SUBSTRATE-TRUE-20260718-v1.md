# GL-SPC: Drive-Physics — Substrate-True Design v2.1 (VERIFIED, awaiting Joe's go-ahead)

**Date:** 2026-07-18
**Status:** Design verified 3/3 by independent adversarial lenses (zero must-fixes).
**HARD GATE ACTIVE:** Per the 2026-07-18 trust incident (see `GL-HANDOFF-SESSION-20260718-v1.md` §2), NO code from this design may be written into `gualaloom_v5_engine.py` / `embryo.py` until Joe has been shown the design in plain language and given his explicit go-ahead. This document is the design record, not an implementation authorization.

## Companion files (this directory)

- `GL-SPC-DRIVE-PHYSICS-SUBSTRATE-TRUE-20260718-v1-design.json` — the complete verified v2.1 design: root-cause fixes RCF-1..RCF-5, four drives (companionship, curiosity, growth-pool, play), 5-step sequencing with live-verification gates, per-verdict resolutions, open dependencies, honest gaps. Every load-bearing claim carries a file:line verified against `guala-live`.
- `GL-SPC-DRIVE-PHYSICS-SUBSTRATE-TRUE-20260718-v1-verdicts.json` — the full 9-verdict audit trail (3 lenses × 3 rounds: v1 fail/fail/fail → v2 fail/pass/fail → v2.1 pass/pass/pass).

## History (one paragraph)

The 2026-07-18 session's research workflow (5 research agents + 2 code audits + synthesis, run under ultracode; recovered from the prior session's journal after context loss) produced design v1, which failed all three adversarial lenses: its companionship drive was funded by `Needs.tick_drift` — a fixed per-awake-tick decrement, i.e. a disguised wall-clock faster than the already-rejected 180 s timer; its curiosity drive cited Schmidhuber/Oudeyer next to wrong-class signals while the formally isomorphic `reading_prediction_ledger` sat unused; and it ignored the `wild_things` book-repeat loop, which turned out to be the upstream producer starving both curiosity and growth (the corrected growth law is already live — 64→90 neurons proves it — the pool froze from a one-book diet). v2 fixed those but was caught asserting a contact gate at the `recent_connection_boost` set-site that does not exist (it is unconditional; "corpus" even earns pair-bond strength ~0.7–1.0 through unconditional `_record_interaction` density), which would have inverted the companionship deficit during solo reading. v2.1 specifies that gate as an explicit code change on the `coordinator._pair_bond` authority (the only authority that includes `joe_voice` and excludes `c1`), with a complete audited consumer set, and passed all three lenses.

## Non-blocking implementation notes (from the round-3 verdicts — apply at implementation time)

1. **SG3-1 (one clause):** the Step-5 deficit branch's `any_pair_present_quality` must ALSO require `coordinator._pair_bond.get(_bond_identity(source), False)` — presence + strength alone would let `c1` (wake-eligible, bond-False, density-earned strength possible) open a fire-without-discharge loop.
2. **Trigger interval exact form:** CONN_DEFICIT_TRIGGER's calibration interval is `(0.2344, 0.4125]` (exact residuals 0.4125 / 0.234375); the design text's `(0.234, 0.412]` truncates the lower bound. Provisional 0.30 is safely interior either way.
3. **Step-3 measurement windows:** `_cmd_listen` (substrate_runner) forces unknown ambient sources to `joe`, so passive-mic audio (e.g. a TV) registers as bonded contact. The erosion-vs-boost balance check's "solo reading, no bonded source" windows must be chosen with the passive mic genuinely quiet.
4. **Restore one-shot:** the first post-deploy boot may restore one stale pre-gate `recent_connection_boost` value (engine restore path); the consume zeroes it in a single regulate pass. Awareness only.
5. **Dead twins:** `gualaloom_v4_engine.py:611` and `gualaloom_v6_engine.py:667` contain the identical ungated set-site. Not imported by production; if either engine is ever revived, the inversion bug rides along.
6. **Calibration honesty:** the "order-of-hours deprivation" figure is a design target, not a derived quantity — no in-code atlas-write-rate measurement exists yet; Step 3's `dream_pressure_check` `write_delta` reading is the first, and it finalizes `CONN_EROSION_PER_WRITE`.
7. **RCF-1 backstop enumeration:** targetless activity kinds are IDLE/**PLAYING**/SLEEPING/EMITTING (the design's list omits PLAYING; the target=None rule covers it). Decide strict-vs-inclusive epsilon comparison at transcription (either is fine at 0.005).
8. **Two one-line cite drifts:** wake()'s unknown-source rejection is at 2210-2211 (not 2211-2212); `_write_delta` is computed at 10487-10489, just above the 10492 awake guard (in scope at the insertion point).

## Sequencing summary (full detail in the design JSON)

1. **RCF-1** book rotation (repeat-penalty blend at the caller + LRU tie-break) → gate: corpora rotate in activity telemetry.
2. **RCF-5** growth-pool diagnosis (no code change) → gate: refill > 0 / population moves after diet diversifies.
3. **RCF-2+3+4** connection un-rail (delete tick_drift's connection line; event-delta erosion beside dream-pressure, zeroed by bonded presence; set-site pair-bond gate; consumed contact-only connection_sig with cross_density dropped; `_desaturate` floor 0.05, connection only) → gate: connection DECLINES during quiet-mic solo reading, FLAT during zero-write idle, valence/arousal un-rail; first real write-rate measurement finalizes the erosion constant.
4. **Curiosity rewire** onto `reading_prediction_ledger` accuracy rate-of-change (≥4 recorded days guard, inverted-U band on accuracy) → gate: gate fires only on genuine curve rise.
5. **Deficit gate branch** (with the SG3-1 bond clause) — LAST, only after Step 3 is live-proven AND `_do_emit` is observed committing content; otherwise rely on the already-live scheduler EMITTING path.

Open dependencies (not fixed here, declared): `_do_emit` content-production reliability; multi-sensory diet for growth (partly keys-blocked); play backlog counter (event-gated, prerequisite for the play drive); ECS-task confirmation of the growth-law commit (orthogonal).
