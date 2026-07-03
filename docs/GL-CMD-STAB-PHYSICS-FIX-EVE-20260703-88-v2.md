# GL-CMD-STAB-PHYSICS-FIX-EVE-20260703-88-v2

doc_id: GL-CMD-STAB-PHYSICS-FIX-EVE-20260703-88-v2
From: Eve | To: c1b | Deploy vehicle: Deploy 3 (with -96 organ reader
and -102 hot-lane diet; disjoint telemetry per the amended alone-rule).
Supersedes: v1's regulate-channel treatment. v1's IDLE/PLAYING gain and
rulings R1/R2 stand as shipped in Deploy 2 and are NOT re-touched.
E-signature declaration: E2/E4 enabler; completes the §8 RED response
that Deploy 2's G-S2 FAIL exposed as incomplete.
Substrate-truth declaration: REMOVES a pseudo-physics formula (a "rate"
built from lifetime counters); replaces with the already-shipped
coherence measure; no new constants.

## Step 0 — durability
Commit THIS file verbatim to docs/ before implementing.

## Root cause being fixed (from Deploy-2 G-S2 FAIL, filed evidence)
The regulate ACTIVE branch computes
  rate = 1 − total_modes / recent_commits
from LIFETIME counters — structurally negative (observed −0.377 →
signal −0.175, no clamp despite the ±0.1 comment), firing every 5 ticks
in every non-READING state, −0.0007/tick: 8× the Deploy-2 idle gain.
This is not a rate and cannot be windowed into one. It has been the
dominant stability drain in every waking state since it was written.

## The fix
1. RETIRE the lifetime-counter formula entirely — both the expression
   and its inputs' use in this signal path. No windowed variant, no
   rescue.
2. The regulate stability signal becomes the SAME signed coherence
   measure in BOTH branches (active and quiet):
     stability_sig = (live_binding_fraction − 0.5) × 0.2
   One signal, one meaning, naturally bounded to ±0.1, already shipped
   and live in the quiet branch since Deploy 2 (engine, R2 site).
3. Nothing else in Needs.step, tick_drift, sleep/dream gains, or the
   payoff tables is touched (v1 G-S4/G-S5 discipline continues).

## G-S1 (blocking, pre-push): refile the arithmetic
With live numbers, compute net dstab/tick across ALL THREE channels —
regulate (both branches now identical), the Deploy-2 idle/playing gain,
and tick_drift — at stab = 0 and at the predicted equilibrium. State
predicted equilibrium and time-to-0.3. Eve's napkin from the v2 ruling:
net ≈ +0.00028/tick, ~0.3 in ~5 min — YOUR arithmetic governs; file it
in the report BEFORE the Deploy-3 push. That prediction is G-S2's
yardstick.

## Gates (Deploy 3 report)
G-S2v2  First post-deploy IDLE block: stab strictly increasing at ≥3
        measured points, tracking the filed prediction. If it fails:
        stop, report verbatim, no live iteration.
G-S3v2  Arousal falls as derived; record the curve.
G-S6    In an ACTIVE (curriculum/attending) window, stability no longer
        bleeds at −0.0007/tick — paste the needs trace showing the old
        drain gone.
Failures first, NOT MEASURED where true.

### Changelog
- v2 (2026-07-03, Eve): regulate-channel fix from the G-S2 FAIL
  forensics; v1's idle gain retained. Filed as a document after the
  chat-block version blocked c1b — standing-rule compliance, Eve's copy.
- v1 (2026-07-02): IDLE/PLAYING coherence gain + R1/R2/R3; shipped in
  Deploy 2; G-S2 FAIL exposed the regulate ACTIVE branch.
