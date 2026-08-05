# Autonomous play single-settlement proof block — 2026-07-27

This is an exact local architecture finding. It is not a production readiness
claim.

## Architecture honesty gate

1. Requested architecture: one authenticated autonomous physical play action,
   one full-field W1 outcome settlement, one learned-state mutation, and
   byte-identical bounded cold restore.
2. Current code reality: the active local play path admits the trigger, settles
   the physical action outcome correctly, then unconditionally creates and
   learns a second post-action settlement.
3. Conflict with requested architecture: yes.
4. Mechanisms not extended: lexical imagination, scripts, labels, ML, chi,
   reduced DSF proxies, scalar play scoring, and duplicate sensory settlement.
5. Single exact next item: remove the duplicate post-action remount from the
   shared engine integration and advance deliberation using the already
   authenticated action-outcome mount.
6. DSF evaluation: the first action outcome contains the full
   `D_k/M_k/R_rev_k/U_star_k/C_k/P_k/B_k` field.
7. Reduced structure lost: none. The defect is duplicate admission, not field
   reduction.

## Exact defect

In local engine file SHA-256
`2e22e5aed38cc284847f83edace3625199e768b3d063e11f85cd540ec79138d0`:

1. `_settle_executed_embodiment_outcome` calls
   `mount_action_outcome(..., commit=False, reserve=True)` at lines
   `9995-9999`.
2. It closes the dispatcher against that exact causal settlement at lines
   `10028-10035`.
3. It passes the same settlement to
   `_record_causal_perception_without_dispatch(..., action_outcome=True)` at
   lines `10036-10044`. This is the correct learned-state mutation.
4. It commits the prepared W1 mount at lines `10045-10047`.
5. After that completed outcome returns, `_run_causal_play_episode` calls
   `mount_current_observation(commit=True)` again at lines `10700-10706`.
6. It records the second settlement through
   `_record_causal_perception_without_dispatch` at lines `10715-10721`.
7. Only then does it advance causal deliberation at lines `10728-10731`.
8. `_atick_playing` unconditionally enters this chain at lines `19038-19043`.

The second record is not an observational status copy. It invokes
`_full_field_prediction_observe`, so it changes learned substrate state again.
Because it immediately follows the already-settled outcome without another
physical action, it can form a false passive continuation or recurrence. That
is the same terminal class currently visible in production's latest
boot-reconciliation play record: `recurrence`.

## Required correction

After `_settle_executed_embodiment_outcome` returns `actual`, the play loop must
use:

- `actual.causal_settlement` as `current_settlement`
- `actual.observation_receipt` as `current_observation_receipt`
- `actual.causal_settlement` as both the next deliberation observation and the
  exact action outcome

The post-action `mount_current_observation(commit=True)` and its second
`_record_causal_perception_without_dispatch` call must not execute.

That preserves:

- one physical action
- one physical outcome settlement
- one full-field learned-state update
- the existing dispatcher closure
- the existing W1 prepared-mount commit
- the exact evidence supplied to deliberation

## Why no proof was added

Any positive test against the current engine must either accept the duplicate
settlement or replace/mask the engine method with a fixture. The requested proof
forbids both. A passing test produced that way would certify the wrong
architecture.

The necessary change is confined to the shared, heavily modified
`dsf_ai_service/v4/gualaloom_v5_engine.py`. This stream did not edit that
overlapping file. Once the owning integration stream removes the duplicate,
the decisive positive test can be added as a new isolated test file and must
prove:

- exact owner-issued opportunity
- one applied physical command
- world revision change
- all seven DSF fields in the single outcome witness
- exactly one learned-state mutation
- consumed opportunity cannot replay
- encoded states remain within their declared byte bounds
- byte-identical cold restore of world, action cycle, teaching,
  deliberation, prediction, and autonomous-play owner
