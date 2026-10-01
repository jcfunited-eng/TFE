# ArcLoom tenth pass audit and implemented boundary corrections

Reviewed commit: `9c6820200d270b31b54f85a8bba5e8b65c52d746`.
Review and corrections completed across 30 September–1 October 2026 UTC.

**Verdict: the receipt does not close the architectural audit. I corrected the
bounded numerical and custody defects, removed the rejected execution
shortcuts, and preserved an explicit unavailable boundary. I did not implement
the missing physical neuron operator or deploy a replacement organism.**

The corrections are isolated in `/tmp/guala-a1-a10-9c6820200`. G1's existing
uncommitted adapter, witness and runner changes in the shared worktree were
not overwritten. The reference paths below describe the isolated correction;
the submitted predecessor remains available by its exact commit.

## Architecture honesty gate

Requested architecture: complete authoritative joint-field delivery through
exact MathLoom and the ratified phase, gate, conductance and material
transition; faithful restoration; actual same-organism causal closure.
Current source: a valid encoder primitive was followed by truncated digit
injection; the producer also synthesized a field by averaging and maxima.
Conflict: yes. Neither operation is the ratified physical mechanism.
Not extended: digit-to-current substitution, averaged DSF, invented stability,
dimensionless contact-law rebranding, endurance fixtures, or production.
Single next item: complete the existing typed field-to-material transition
contract with derived mounted parameters, then implement that one transition.
This audit and its tests are reduced numerical, source and native-boundary
checks. They do not evaluate joint physical settlement, whole-organism
learning or a deployed cognitive replacement.

The project-truth and neuron-physics skills require unavailable physical
couplings to remain unavailable rather than substituting a new scalar or
threshold. That requirement is why the local candidate refuses unsupported
execution; it is not a claim that refusal completes the requested cognition.

## What this submission really repaired

| Prior item | Assessment of submitted source |
| --- | --- |
| A9-01 motor boundary | Accept matching native limits and strict integer 250,000-microsecond duration. The world obstacle check uses the actual efferent tuple. Whole-organism motor authority is still not established. |
| A9-02 plastic return | The dimensionless update now projects its trial stress to the yield surface. Accept that algebraic change and the retracted SI claims; do not certify material physics. |
| A9-03 restoration | Accept required native predecessor layouts, current v4 rejection, checked shared-column count arithmetic and a structurally targeted asymmetric-tract test. Ordinary organism restoration still invoked migration automatically; corrected below. |
| A9-04 representation | Accept the new exact binary64-to-rational encoder primitive. Reject the consuming truncation and fabricated producer. |
| A9-05 retention and cold comparison | Accept the narrowed component-retention wording, paired native successor bytes, matching committed receipts and complete fresh-world snapshots. This still is not a paired organism/world cold continuation through ordinary settlement. |
| A9-06 runner | Accept finite recent receipts and online summaries replacing lifetime sample lists, plus explicit fixture disclosure. This remains an open-loop fixture runner, not proof of physical full-field autonomy. |

These are source assessments, not a claim to have independently rerun every
suite in G1's receipt.

## A10 numerical defect and completed correction

The actual predecessor functions were compiled into a tiny isolated arithmetic
probe before editing. Results:

| Input or condition | Submitted behavior |
| --- | --- |
| Numerator digit `2`, denominator `1` | Accepted as `0.0`, although 2 is not a balanced trit |
| Nonzero numerator with `is_zero=True` | Accepted as `0.0` |
| Exact integer `2^53 + 1` | Silently returned `2^53` |
| `a=2^-52`, `b=(2*3^32+1)/2^52` | Distinct full encodings, identical 32-trit numerator prefixes and identical denominators |

Both a and b lie strictly between zero and one. Their binary64 values are
`2.220446049250313e-16` and `0.8229062715034281`. The conjugate projection
does not recover the discarded positions.

Implemented: [native exact arithmetic](../native/guala_core/src/mathloom.rs)
now rejects non-trits, empty/overlong/noncanonical integers, inconsistent
sign/zero metadata, unreduced fractions, invalid denominators, overflow,
off-grid subnormal values and loss of precision. Signed zeros and exactly
representable values round-trip bit-for-bit. The native module is extracted
once per existing distribution, not duplicated across runtime authorities.
The 18-word arithmetic and 679-trit limit derive from finite binary64's
maximum numerator and `2^1074` denominator.

Both existing Python adapters now pass typed digits without coercing
fractional numbers, strings or Boolean metadata into different evidence.
References from: binary64 result and native/Python codec callers.
References to: exact numerical carrier and storage checks.
Impact: malformed evidence fails explicitly; valid finite binary64 encoding
and checkpoint format remain unchanged.

## A10 full-field substitution and completed containment

Submitted `step_cycle` copied only the first 32 numerator trits and first
32 denominator trits into each primary/conjugate column. Even retaining
more digits would not supply the authorized phase/material operator.
Laminar sums and thresholds treated those digits as direct afferents.

Implemented in [native transition](../native/guala_core/src/cortical_column.rs):
removed that projection and the obsolete truncating helper. A present field
now produces an explicit native error, translated to Python
`NotImplementedError`, before native trace, motor, neuronal or plastic
mutation. Restored present fields behave identically. Legacy sensory slots
48–63 can no longer resurrect direct DSF digit injection. Component-only
recurrent execution remains distinct from full-field execution.

The submitted organism also replaced the prior single-channel selection with
means of D/M/C/P/B, maxima of reversal/uncertainty, and `S_UF=B-P`.
That is a new reduction, not the complete joint field or canonical global
stability. In [the organism producer](../dsf_ai_service/guala_functional_organism.py)
I removed this construction and made its unavailable shared-field boundary
explicit. No alternate field, default stability, larger array or learned
weight substitute was introduced.

References from: organism `_form_moments`, bridge `ingest_and_step`,
continuous-field restore and native `step`.
References to: recurrent state, plasticity, efferents and subsequent
body/world execution. **Operational impact: deploying this candidate into
the current organism would refuse the unsupported path. It must not be
deployed as a functioning cognition release.** The native refusal is proven
atomic; this does not prove a whole-organism transaction rollback.

The original positive field witnesses remain visible as strict expected
failures, not converted into passing cognition claims. Their other accepted
checks remain in place. New negative tests prove truthful refusal only.

## A10 current-only restoration correction

Although adapter `from_dict` was current-only, the organism's
`_modular_substrate` property automatically dispatched old formats to
migration and rewrote stored state on a read. I removed that branch.
Ordinary restoration now uses the existing current-only decoder. Explicit
migration APIs remain separate and require predecessor layout metadata.

Impact: legacy checkpoints require their deliberate one-time migration before
startup; reading the ordinary property cannot silently alter their generation.
The focused test executes the actual property with the real adapter and
native storage. It verifies current-byte equality and rejection of historical
formats without caching or rewriting them. It is a custody-routing test, not
a whole-organism replay. Layout strings alone still do not authenticate a
historical build; actual predecessor provenance remains a release prerequisite.

## Remaining physical implementation contract

**Do not declare all findings closed.** The exact numerical representation is
not the missing neuron. The dimensionless `pre*post-w` return map still
does not derive mounted mechanical stress, work-conjugate variables,
conductance geometry or material energy accounting. Changing its rate to
an immediate projection fixes the previous algebraic counterexample, not
that architectural gap.

The single next implementation is the already specified causal path:

`shared typed UF result -> exact rational trits -> typed Psi/Krimelack
constraints -> phase settlement -> channel gate displacement ->
conductance/current -> native state -> motor/world consequence ->
same-organism sensory return`.

Its necessary completion requirements are:

1. Carry the canonical shared field's typed vertices, topology, locality,
   interval and source reference, with the real separate global `S_UF`.
   Do not average channel results or substitute `B-P`.
2. Use the ratified trit constraint
   `E_DSF = -kappa_qp sum cos(phi_b-phi_a-2*pi*tau_qp/3)`.
   The positional index is exact significance, not an arbitrary energy
   weight. Derive coupling and phase dissipation from mounted anatomy.
3. Couple settled phase through the specified gate potential and
   `g = sigma*A(y)/ell`, with derived units and material parameters.
   The missing executable values/functions include mounted coupling,
   gate potential, aperture geometry, damping and supply/work accounting.
   No compatible mapping of those quantities is present in this candidate.
   Existing `constitutive.rs` and `coupled_synapse.rs` are explicitly
   unmounted and cannot be asserted to be drop-in closure merely because
   they contain physical equations.
4. Preserve the actual physical state through paired organism/world
   persistence, cold restoration and the next ordinary interval. Exercise
   the real caller, actual committed action and returned receptors; matched
   fresh worlds and component probes alone do not satisfy this boundary.
5. Only after this operator and its parameter authority exist should the
   explicit unavailable boundary be replaced and the positive causal witness
   be required to pass. Absence of expected failures is a release condition,
   not something to hide in a green total.

This is a concrete integration contract, not a request for Joe to choose
implementation details. The missing mounted physical definition cannot be
truthfully filled by another threshold or label.

## Executed verification and delivery limits

- Predecessor arithmetic probe reproduced the three decoder faults and the
  normalized-range projection collision using the submitted functions.
- Six direct tests of the production arithmetic module passed in 0.66 s;
  one enumerates 24,564 sign/exponent/mantissa cases across every finite
  exponent, including subnormal and maximum-exponent boundaries.
- The isolated root native release build succeeded in 18.25 s, offline,
  with two build jobs. One unrelated existing unused-variable warning remains.
- Seven focused Python/native/source checks passed in 0.24 s
  (0.394 s process wall time; measured child peak RSS 82,560 KiB).
  Source anti-resurrection checks are identified as such, not physical proofs.
- Loaded extension:
  `9a5756e4d1021be7d5b370d1cb3faaadeff4babc0b3c689554e2637a86c1d27e`.
- Root and standalone numerical module hashes match:
  `ba117fccfd00f23753da1ad9f0c07a8056c34771091ab350b2db795f4459db3e`.
  Corrected native column sources also match:
  `ffcb71c072628c133f6d860aeb4d9f3a5219fc13fac4f969d66347bbea3237c7`.
- No endurance run or broad organism suite was started. No claim is made that
  the previous 44/6/19/14/6 reported counts remain whole-system acceptance.
  Archives were not rebuilt and still contain the submitted code, not this
  correction. They are not corrected release artifacts.
- Read-only production observations before/after reported the same identity,
  available=true, no checkpoint error and no durability block, with live tick
  advancing from 3,215,427 to 3,215,902. These are point observations, not an
  ECS release-identity audit or proof of the production cognitive architecture.
  No live state, caretaker control, task or deployed artifact was changed.
- Post-test process census found no remaining cargo/rustc/maturin/pytest/A10
  test processes. The isolated worktree and its small build artifacts are
  intentionally retained. The missing /usr/bin/time utility was handled once
  with Python's standard resource measurement; the failed launch ran no test.

**Recommended disposition:** retain these numerical/custody corrections and
explicitly reject full-causal-closure certification. G1 should use the one
physical integration contract above, not launch the proposed endurance run
or deploy this refusal-boundary candidate as a cognition fix.

