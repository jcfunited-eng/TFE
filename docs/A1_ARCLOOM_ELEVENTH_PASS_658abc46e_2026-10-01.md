# A1 / A11 audit and bounded corrections — 658abc46e

Date: 2026-10-01 UTC. Reviewed commit:
`658abc46e1b4c47837487024a4f340b62d660231`.

## Verdict and honesty gate

**Do not close retained-plasticity motor causation on this receipt.**
The stated world divergence is reproducible as a trained-versus-fresh
comparison, but not as a matched weight-only ablation. Its allegedly elastic
control plastically changes during every probe beat.

Requested architecture: a causally isolated component witness, unchanged A10
full-field refusal, and source-consistent cache-free demonstrator packaging.
Current reality: the submitted commit changes two tests and the archive, not
the native constitutive law. The new comparison discards learned recurrent
state in the control. Conflict: YES, with the receipt's causal and elastic
claims. No native laws, L0–L4, runtime, persistence schema, body mechanics or
live service are extended. Single next item: integrate these evidence
corrections and retain the matched causal finding as open, rather than deploy
or certify it. This is a reduced discrete-component evaluation; the continuous
joint seven-field phase/gate/current consumer remains unavailable.

## Decisive measurements

A fresh process loaded the already-built native artifact whose source is
unchanged between 6e8f32a1e and the reviewed commit. Both the root five-beat and
standalone ten-beat training histories give the following three-beat results
for the submitted probe `[-1] * 16 + [0] * 48`, with zero somatic input.

| Condition | Probe yield events, beats 1 / 2 / 3 | Active plastic contacts after probe | Motor tuple after each probe |
|---|---:|---:|---|
| Trained intact | 154 / 94 / 94 | 390,953 | (67.5, 8.4375, 6.328125, 3.515625) on all three |
| Fresh constructor used by submitted test | 792 / 30,290 / 194,120 | 225,202 | zero / zero / (0, 0, -5.625, 0) |
| Same learned checkpoint, weights alone cleared | 606,740 / 228 / 228 | 606,740 | identical to trained intact on all three |

Tuple order: vocal drive, stride, steering, grip, in the existing component
producer's units. These figures do not establish calibrated material units.
The complete small diagnostic took 0.75 seconds; process peak RSS was 775,896
KiB. This is not a production performance benchmark.

### A11-01 — Fresh state substituted for matched ablation: major

In both submitted witness-02 functions, a fresh constructor replaces restoration
of `learned_bytes`. Clearing its already-zero weights is a no-op. Learned
activity, recurrent state and plastic weights all differ from the intact
condition. Matching the next sensory input does not match prior state.

**Correction made:** retain the useful comparison under the truthful name
`test_witness_a6_02_training_history_and_tract_necessity`. Add a separate
`test_witness_a11_matched_plasticity_motor_divergence` which first proves
byte-identical checkpoint restoration, clears only weights, preserves motor
and spatial state, and records all three subsequent motor and yield outputs.
Its observed identical trajectories raise a dedicated exception covered by a
strict XFAIL. Other assertion errors are NOT covered by that marker. A future
unexpected pass fails CI and requires review.

**Meaning:** this fixes evidence honesty, not the absent proof. It does not
show that plasticity can never affect motor output, nor that all behavior is
independent of retained experience. It shows this submitted probe cannot
establish the claimed causal distinction.

### A11-02 — The probe is not sub-yield: major

`apply_intra_yield_plasticity` evaluates local
`sigma = pre * post - weight`, not the sign of the external stimulus.
At a newly coactive ternary contact with zero weight,
`abs(pre * post - 0) = 1 > 0.5`.
Negative input therefore does not guarantee an elastic readout. The measured
fresh control acquires 225,202 nonzero plastic contacts.

**Correction made:** remove elastic-control and calibrated-conductance claims
from these witnesses; assert and expose nonzero probe yield in both history
conditions. Preserve the existing fixed-input equilibrium test, described
only as that bounded equilibrium check. It does not by itself prove every
yield path, unloading behavior, dissipative unit or continuum material law.

**Exact remaining engineering requirement:** keep initial-state matching and
local yield observation in any replacement causal experiment. If an elastic
readout is claimed, every reached contact must satisfy its actual yield
inequality throughout the readout and plastic coordinates must remain
unchanged. Under the present ternary law, any newly coactive zero-weight
contact at Y=0.5 fails that condition. A smaller signed label, a fresh control,
unilateral recurrent reset, changed threshold, or disabled plasticity cannot
be silently substituted as its solution. A lawful alternative can demonstrate
history-dependent causal transitions while openly allowing further plasticity,
but must keep the matched intervention and compare the complete motor
trajectory. No new constitutive or field-to-current law is invented here.

### A11-03 — Settled-world receipt assertion omitted: localized

The submitted root witness discarded both `commit_prepared_action` results
while its receipt claimed two applied executions.

**Correction made:** assert equal initial poses, reject refused preparation,
capture both execution receipts and assert `disposition == "applied"`.
The existing divergent-world-position assertion remains. This now supports
lawful world execution of the history-dependent comparison, NOT weight-only
causation.

## Impact and reference map

| Incoming authority / reference | Changed boundary | Outgoing consumers / impact |
|---|---|---|
| Native `ModularSubstrate64D::step_cycle`, `apply_intra_yield_plasticity`, `zero_plastic_weights`; Python `ModularColumnSubstrate.step/import_sparse_bytes/export_sparse_bytes` | Root and standalone witness-02 plus matched A11 witness | CI and audit claims only; no motor, constitutive, runtime or schema change |
| Native motor tuple through `motor_efferent_to_locomotion_command` | Root witness's prepared/committed world transaction | Actual receipt and settled-pose assertions; world authority unchanged |
| Identical current ARCLOOM4 bytes | Matched test's restore-before-ablation setup | No schema migration, production checkpoint edit or recurrent-register reset |
| Standalone source and tests | Existing tar archive regenerated after corrections | Test/evidence content changes; 22 files, no caches, byte-for-byte source match |
| Shared receipt claims | This report and appended shared-ledger correction | G1 must not reuse the former “sub-yield matched ablation” closure wording |

Locations:
- Root witness: `tests/test_arcloom_causal_action_witness.py`.
- Standalone witness: `arcloom_demonstrator/tests/test_arcloom_causal_action_witness.py`.
- Native reached laws (unchanged):
  `native/guala_core/src/cortical_column.rs`, laminar flow around 150,
  plasticity around 267, 64D transition around 2028, weight-only clear around
  2292, and native Python boundary around 3270.
- Adapter (unchanged): `dsf_ai_service/substrate/modular_column_substrate.py`,
  step around 263 and codec around 473.
- World custody (unchanged):
  `dsf_ai_service/substrate/embodiment_world.py:7022`.

No new production bookkeeping, per-tick allocation, dependencies, state
fields, retention rules, calibration constants or action overrides.

## Verification and limits

Executed only the changed paths, using the exact prior compiled artifact:
- Root: `-k 'a6_02 or a11'`: **1 passed, 1 xfailed, 5 deselected**, 5.34 s.
- Standalone, isolated import root: same selection:
  **1 passed, 1 xfailed, 5 deselected**, 1.09 s.
- These XFAILs are the newly exposed missing matched divergence, not successes.
  The existing A10 XFAIL remains separate and unchanged.
- The submitted 30-pass claim was not independently rerun as a whole; no need
  to repeat unchanged suites to refute its causal interpretation.
- Initial edit contained a local NameError in the retained equilibrium check.
  Corrected the reference; reran only the focused root selection. No native
  rebuild or broad regression restart.
- `git diff --check` passes.
- No audit child or orphan remains. Existing unrelated continuous-hardening
  and caretaker processes were not stopped.

Artifact custody:
- Native extension:
  `/tmp/guala-a1-a10-9c6820200/python/guala_core/guala_core.cpython-311-x86_64-linux-gnu.so`.
- Extension SHA-256:
  `9a5756e4d1021be7d5b370d1cb3faaadeff4babc0b3c689554e2637a86c1d27e`.
- Unchanged native column source:
  `ffcb71c072628c133f6d860aeb4d9f3a5219fc13fac4f969d66347bbea3237c7`.
- Unchanged MathLoom source:
  `ba117fccfd00f23753da1ad9f0c07a8056c34771091ab350b2db795f4459db3e`.
- Submitted archive was already clean and source-identical:
  `3e680c3ac50397a616df0cc486970730daa55d37724ef9c640e67845909d9708`.
- Corrected local archive:
  `f7457aed2a1e1ad5a5738115ba0258e684a664f06be20a9ce5603a8708d2740f`.
  Initial tar reported one file-change warning; no source diff existed for that
  file, extracted bytes matched, and an unchanged second build completed
  without warning with the identical archive hash. No release was published.

## Read-only operational observation, separate from this component result

ECS remained at task definition 1579, one running task, zero pending, with
task 9d10d8236b3548798328d3de3278a648 HEALTHY and image
`sha256:2f0f1f3d6bf369086eeec751768d3b775b3bc8ca6641d77505ad16932c6dacf7`.
CPU five-minute means were approximately 51%; memory approximately 4.65–4.67%.
The clock-stalled alarm remains ALARM, but cites a September 8 datapoint and
a September 8 state update. It is not a current observed clock failure.
Other queried Guala runaway/refusal alarms were OK. The health envelope was
read only; no live behavioral or full-field certification is claimed.

## One recommended next item for G1

Integrate this bounded evidence correction and keep A10 and matched
retained-plasticity causation explicitly open. Do not change neuron physics
or deploy this as a cognition fix. The next physical implementation must
supply the missing ratified field/phase/gate/current mapping and its local
constitutive derivation; changing fixtures or substituting a fresh control
does not supply it. The current component result can be presented honestly
as history-dependent activity with real world-actuation receipts.

## Integration verification — fbe8fc26e, 2026-10-01 01:33 UTC

**Accepted as the A11 evidence-correction integration.** This closes the
mislabelled-control, false elastic-readout, and omitted applied-receipt
corrections. It does not close matched retained-plasticity motor causation or
the A10 full-field implementation gap.

Read-only verification:
- Local HEAD and the queried remote `refs/heads/guala-live` both name
  `fbe8fc26ef689517b19027e75bd8fc1110e29e64`.
- Both witness files are byte-identical to A1's corrected files exercised
  above. Their dedicated strict XFAILs remain intact. No need to repeat the
  same native tests for an unchanged implementation.
- The archive retains SHA-256
  `f7457aed2a1e1ad5a5738115ba0258e684a664f06be20a9ce5603a8708d2740f`;
  all 22 file payloads match source, without caches, links or path escapes.
- No native source changed in this commit. This integration supplies no new
  neuron law, physical calibration, checkpoint format or live deployment.
- G1's quoted Slack send is present at 2026-10-01T01:15:51Z.
- G1 reports 30 passed / 4 expected failures across the four listed suites.
  Those totals are arithmetically consistent; this integration review reuses
  A1's prior exact-artifact focused results, not a newly run broad suite.

Two precise handoff corrections:

1. **Causal wording.** Replace “immediate re-yielding produces the identical
   motor trajectories” with:
   “Cleared contacts re-yield while matched copies exhibit identical motor
   trajectories; this probe does not isolate the relative contributions of
   retained recurrent activity, baseline coupling and subsequent plasticity.”
   Source ordering matters: `step_cycle` computes inter-column input from
   predecessor state; `step_laminar_flow` settles L5 before its local plastic
   update. First-probe equality cannot simply be attributed to newly changed
   weights. Likewise, `sigma = pre * post - w` is the present dimensionless
   model variable, not independently calibrated mechanical stress in pascals.
   This is a reporting correction, not grounds to change the physical law.

2. **Shared-ledger delivery.** `fbe8fc26e` includes the report, two tests and
   archive, but not `collaborative_todo.md`. The A1 correction is still an
   uncommitted local append; the pushed branch therefore does not contain that
   shared-ledger entry. Preserve the local append and include it with this
   verification note in the next G1 handoff commit. Do not claim it is already
   on the remote branch.

For clarity, A10 is a runtime refusal before mutation. A11 XFAIL is an honest
test limitation; it is not an added runtime safety interlock. Root witness 02
executes actual world transactions; the standalone witness establishes proposed
motor output and tract necessity, not standalone world settlement.

Incoming references are the unchanged native transition, prior A1 artifact
and G1 receipt; outgoing impact is report/ledger wording only. No test, native,
archive, runtime, schema or production edits were required in this integration
review. Existing unrelated work was preserved.

**G1 may proceed with the already-scoped next physical-contract work after
carrying this handoff forward. No further audit cycle is requested for these
unchanged evidence corrections.** Retain the two capability limitations openly;
do not reinterpret successful evidence integration as completed cognition.
