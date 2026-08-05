# GL-CMD-STAB-PHYSICS-FIX-EVE-20260702-88-v1

doc_id: GL-CMD-STAB-PHYSICS-FIX-EVE-20260702-88-v1
From: Eve | To: c1b | Deploy vehicle: Deploy 2
Spec source: GL-RPT-STAB-PHYSICS-C1-20260702-99-v1 §A.4 (c1a), adopted
with three Eve rulings below.
E-signature declaration: E2/E4 enabler — restores the quiet half of the
intake→quiet→dream rhythm (spec P2); §8 RED mandated response.
Substrate-truth declaration: no new tuned constants — every factor is an
existing measured quantity or existing constant; one hardcoded penalty
constant REMOVED (−0.05 bored branch); scheduler promise made honest.

## Step 0 — durability
Commit THIS file verbatim to docs/ before implementing.

## The fix (A.4 shape, adopted)
Quiet-coherence stability gain in IDLE and PLAYING:

  dstab_per_tick = coherence x max(0, TARGET - stab) x NEEDS_DRIFT_RATE / TARGET

Touch points: new IDLE branch in the activity dispatch (engine
:5010-5026); same line in _atick_playing (:4593); bored-branch
replacement per Ruling 2. Engine-only, ~10-20 lines, no schema, no env.

## Eve rulings
R1 COHERENCE SOURCE = atlas live-binding fraction
   (n_live_bindings / n_total_entries, already computed for
   atlas_health). NOT reinforcement_rate: that quantity is
   definitionally absent during quiet (only computed when
   recent_commits > 0) — using it would zero the gain in exactly the
   state the gain exists for, recreating the bug with extra steps.
   Rest over a coherent atlas restores; rest over noise does not.
R2 The hardcoded −0.05 "bored" nudge (:1127-1129) is REPLACED by the
   same signed coherence measure — a bare penalty constant is §9.1
   prohibited class, and quiet must not be punished by one channel
   while another repairs it.
R3 PRE-DEPLOY ARITHMETIC (evidence before code, blocking): using live
   numbers (coherence ≈ 0.876, stab = 0.000, NEEDS_DRIFT_RATE = 0.0001,
   regulate cadence 1-per-5-ticks), compute net dstab/tick under the
   full fix INCLUDING drift and the replaced regulate channel. Show it
   is net-positive at current coherence and state the predicted
   equilibrium stab and time-to-0.3. If the arithmetic comes out
   net-negative or marginal, derive the drift term into the same
   equilibrium framework (symmetric distance-to-target scaling) — no
   tuned rescue, and re-show the arithmetic. The prediction goes in
   the report BEFORE the deploy and becomes the gate's yardstick.

## Gates (Deploy 2 report)
G-S1 The R3 prediction filed pre-deploy, arithmetic shown.
G-S2 First post-deploy IDLE block: stab strictly increasing, measured
     at ≥3 points, tracking toward the predicted equilibrium.
G-S3 Arousal falls as derived (no code touched for it) — record the
     curve; note nov/conn above-target hold it ≥~0.51 (a later,
     separate mandate — do not touch here).
G-S4 SLEEPING/DREAMING gains unchanged; no other needs channel altered.
G-S5 ACTIVITY_STABILITY_PAYOFF["IDLE"] untouched — the point is that
     its promise becomes true, not that the table changes.
Failures verbatim. If G-S2 fails, the fix does not get iterated live —
report and stop.

### Changelog
- v1 (2026-07-02, Eve): first filed version, from -99 §A.4 with rulings
  R1-R3. The §8 RED response, outstanding since the vitals table was
  written, finally dispatched with its root cause in evidence.
