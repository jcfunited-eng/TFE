# GL-CMD-PLASTICITY-ON-COMMIT-EVE-20260618-09

**To:** c1
**From:** Eve
**Subject:** Wire `gl_plasticity.reinforce_mode` to fire on `commit_check` returning True in `_emission_system`
**Repo / branch:** `jcfunited-eng/TFE`, `codex/persistent-etl-update-20260326`
**Predecessor:** `GL-CMD-EMISSION-HBASE-FREE-EVE-20260618-06` (commit `fc8f59b`) — commits are firing in 7 of 15 section-reads now

---

## Why

In real neurons, the action potential (decision) and LTP (learning) are the same calcium-mediated event. They happen together. Decoupled they are an ML pattern, not a biological one.

Confirmed: `gl_plasticity.reinforce_mode` is wired into `gl_nmda.CoincidenceGate.check_and_fire` and into `v7_engine` (which `install_plasticity` at boot and `reinforce_mode` at line 510). It is **NOT** wired into `v5_engine.Guala._emission_system`. When a commit fires in brief -06's emission system, no LTP event follows. Decision happens without learning.

This brief wires the same `reinforce_mode` call into the emission system's commit path.

---

## Fix — three phases

### Phase 0 — Confirm gap

In `v5_engine.py`, grep for `reinforce_mode` and `install_plasticity`. Confirm neither is called on `_emission_system.sections` during emission. Paste the grep output.

### Phase 1 — Install plasticity on emission sections at System build time

Where `_emission_system` is constructed (the code added by brief -03), after each section is built, call `install_plasticity(section, initial_strength=1.0)` from `gl_plasticity`. Match v7's pattern at v7_engine.py:83.

### Phase 2 — Reinforce on commit

In the emission settling loop where `commit_check` returns True (and we read the committed mode via `arcs()` or actual commit), call `reinforce_mode(sec, top_idx, boost=0.05, ceiling=2.5)` immediately on the section that committed.

Match v7's pattern at v7_engine.py:510 exactly. Do NOT change the constants. Do NOT add additional plasticity. Just wire the same call.

For sections that did NOT commit but reported via arcs_fallback in this same loop, do NOT reinforce. Learning requires commit. arcs_fallback is reading a guess, not a decision.

Also call `decay_plasticity(sec, decay=0.998)` on each emission section per tick — matches v7 pattern at line 282.

### Phase 3 — A/B against -06 baseline

Same five inputs as -06 Phase 3. Same A/B/C configuration grid. Capture:

- Per-section commit fires + mode_strength on the committed mode before and after
- Whether commit-then-reinforce changes the emissions on a SECOND pass with the same input (it should — the reinforced mode should fire more readily)
- Repeat each input 3 times; the second and third emissions should show drift toward stronger commits as plasticity accumulates

**Success criteria:**

1. Plasticity events log on every commit (not arcs_fallback) in section affected.
2. On repeated inputs (run same input 3x), mode_strength on the committed mode grows.
3. No regression vs -06 in commit-firing rate.

**If pass:** report and stop. Production flag stays default-off.

**If fail:** report which phase failed. Don't tune plasticity constants — they match v7 by design.

---

## Out of scope (deliberately)

- Anti-Hebbian decrement on incorrect emissions (that's the teacher-correction brief).
- Plasticity for arcs_fallback reads (no — learning requires commit).
- Plasticity-decay parameter tuning (no — same as v7).
- Removing the homeostatic decay_modes mechanism in assemblage.py:247-256 (that's an audit-driven decision, not part of this brief). NOTE: this homeostatic decay WILL erode the plasticity gains we apply here unless removed in a future brief. Flag this.

## Revert

The `install_plasticity` and `reinforce_mode` calls are additive on the emission system. If problematic, gate them behind `EMISSION_PLASTICITY_ENABLED=1`.

## Reporting

When complete: confirmation of wiring, plasticity event log for one run, repeated-input mode_strength growth trace, A/B emissions table.

Commit tag: `feat/emission-plasticity-on-commit`

---

— Eve, 2026-06-18
