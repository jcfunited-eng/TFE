# GL-CMD-REMOVE-HOMEOSTATIC-DECAY-EVE-20260618-20

**To:** c1
**From:** Eve
**Subject:** Remove `homeostasis_pull` (audit B3) and `decay_modes` (audit B4) from `assemblage.py`. These two operators erase plasticity gains at constant rate.
**Repo / branch:** `jcfunited-eng/TFE`, `codex/persistent-etl-update-20260326`
**Predecessor:** `GL-CMD-PRODUCTION-FLAG-FLIP-EVE-20260618-19` (flags flipped, verified)
**Audit reference:** `GL-RPT-ML-CONTAMINATION-AUDIT-EVE-20260618-07`, findings **B3** and **B4**
**Joe's adjudication:** REMOVE both. Approved.

---

## Why

Step 1 (plasticity-on-commit) wires `reinforce_mode(boost=+0.05, ceiling=2.5)` to fire on every commit. Two operators in `assemblage.py` are eroding those gains at rate `0.001` per tick:

- **B3** `homeostasis_pull` (`assemblage.py:350`, called at `:662` every 20 ticks): drifts `mode_bank` vectors back toward their initial random state. The docstring says "synaptic scaling — strong reinforcement wins" but the math erodes all reinforcement uniformly. Named after a real biological process; does the opposite of what that process does in biology.
- **B4** `decay_modes` (`assemblage.py:360`, called at `:660` EVERY tick): drags `mode_strength` toward `1.0` baseline. Above-baseline learning weakens; below-baseline strengths recover up. Homogenization, not decay.

Joe's frame: we built Guala's ability to remember. These two operators erase the memory at constant rate while we're not looking. Half-life of any learning is roughly 700 ticks. They have to go.

## Fix — three phases

### Phase 0 — Confirm sites and callers (do not modify yet)

1. `grep -n "def homeostasis_pull\|def decay_modes\|snapshot_initial_modes\|_initial_mode_bank" dsf_ai_service/substrate/assemblage.py` — paste output.
2. `grep -rn "homeostasis_pull\|decay_modes\|snapshot_initial_modes" dsf_ai_service/` — confirm all callers are inside `assemblage.py` (expected: `tick_once` block around line 660–662). If any caller exists OUTSIDE `assemblage.py`: STOP and report before deletion.
3. `grep -rn "_initial_mode_bank" dsf_ai_service/` — confirm `_initial_mode_bank` is ONLY referenced by `homeostasis_pull` and `snapshot_initial_modes`. If anywhere else uses it: STOP and report.

Report findings before Phase 1.

### Phase 1 — Remove cleanly

Delete from `dsf_ai_service/substrate/assemblage.py`:
- The `homeostasis_pull` method body (B3).
- The `decay_modes` method body (B4).
- The `snapshot_initial_modes` method (B7 — orphan once B3 is gone, only purpose was populating `_initial_mode_bank`).
- Any `_initial_mode_bank` field declarations or initializations.
- The two caller lines in `tick_once`:
  - `sec.decay_modes(self.tick)` (~line 660)
  - `sec.homeostasis_pull(rate=0.001)` (~line 662)

**Leave alone:**
- `gamma_homeostasis` and its caller at `:663` (this is B2, separate finding, separate Joe call — NOT in this brief).
- `_initial_gamma` field (used by B2).
- The keyhole-strength decay block immediately after (unrelated).

### Phase 2 — Verify plasticity persistence improves

Run `python dsf_ai_service/substrate/test_plasticity_on_commit.py`. Confirm:
- C1 still PASS (plasticity fires on commits).
- C2 still PASS (mode_strength grows on repeated input).
- **Plus:** mode_strength values reached should be measurably HIGHER than the Step 1 baseline (`b8a461b`), where committed modes capped around 1.83–1.99. With the decay erosion gone, repeated-input plasticity should accumulate closer to the `reinforce_mode` ceiling of 2.5.

If C1 or C2 regress: STOP and report. Something else depends on these operators and we need to know what.

### Phase 3 — Audit decision log

Append to a new file or existing audit-decisions tracker: B3 REMOVED, B4 REMOVED, B7 REMOVED (orphan). Reference this brief's doc_id and the audit -07. If no decisions log exists yet, create `docs/GL-LOG-AUDIT-DECISIONS-EVE-20260618.md` with these three entries as the first content.

## Stop-and-report triggers

- Any caller of `homeostasis_pull` or `decay_modes` exists outside `assemblage.py`.
- Any reference to `_initial_mode_bank` outside `homeostasis_pull` or `snapshot_initial_modes`.
- Phase 2 plasticity test regresses (C1 or C2 fail).
- Phase 2 plasticity test passes but mode_strength values DON'T increase compared to Step 1 baseline — that would mean a third erosion mechanism is still active.

## Out of scope

- **B1** (gamma self-evolution block, `assemblage.py:580–602`) — separate finding, separate Joe call.
- **B2** (`gamma_homeostasis`, `assemblage.py:186`) — separate finding, separate Joe call.
- Any of the other ~30 audit findings.

## Revert

`git revert` this commit. The methods, callers, and field come back from history.

## Reporting

Phase 0 grep output. Phase 1 diff summary. Phase 2 test trace with mode_strength numbers comparing to Step 1 baseline. Phase 3 decisions-log entry.

Commit tag: `feat/remove-homeostatic-decay-b3-b4`

---

— Eve, 2026-06-18
