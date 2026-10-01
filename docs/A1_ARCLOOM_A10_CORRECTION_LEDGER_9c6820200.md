# A10 bounded correction ledger

Baseline: `9c6820200d270b31b54f85a8bba5e8b65c52d746`.
Owner: A1. Isolated worktree: `/tmp/guala-a1-a10-9c6820200`.
The shared worktree already has other edits to adapters, witnesses and the
runner. Those edits are not included or overwritten.

## Active deliverable

Correct exact MathLoom representation at the native boundary and remove the
unauthorized truncated digit-to-neuron execution path. This is not a new
plasticity law, a full neuron implementation, or a production release.

Entry evidence: the submitted encoder creates complete rational trits, but
`ModularSubstrate64D::step_cycle` takes only 32 numerator and 32 denominator
trits. `float_to_balanced_ternary` silently truncates too. The rational decoder
accepts non-ternary digits, inconsistent zero/sign metadata, and silently drops
unrepresentable low bits. The ratified phase/gate material operator is absent
from this consumer; a longer afferent array is explicitly not its replacement.

## Impact map and authorized files

* Native binary64 input -> exact numerator/denominator representation -> native
  and Python codec callers. Extract one numerical module from
  `native/guala_core/src/cortical_column.rs`, with its tests adjacent; register
  it in `lib.rs`. No L0-L4 equations change.
* Full-field storage/current restore -> `step_cycle` -> Python `step` ->
  adapter/organism and bridge callers. Unsupported full-field execution must
  refuse before any neuron, motor, trace or plastic state mutation. Preserve
  the stored field and checkpoint format. Component-only execution without
  a full-field claim remains separately available.
* Mirror native corrections in `arcloom_demonstrator/native/guala_core/src/`;
  remove lossy integer coercion from the numerical wrapper in both existing
  adapters. Do not rebuild or certify old archives as corrected.
* Replace only the false field-closure assertions in the existing causal
  witness; retain accepted motor, restore, sleep and component comparisons.

The field-to-phase-to-gate-to-current operator and material parameter
derivation remain architectural blockers, not an invitation to synthesize a
new rule. Existing dimensionless return-map code is not extended.

## Exit tests

First reproduce predecessor decoder failures using its actual extracted
numerical functions. Then test the corrected numerical module directly:
finite binary64 bit round trips, signed zero, every finite exponent, malformed
trits, inconsistent metadata, noncanonical fractions, precision loss,
subnormal-grid rejection, bounded arithmetic and the prior 32-trit collision.
At the native interface verify unsupported full-field execution and restored
full-field execution refuse atomically; absence preserves component behavior.
Build only the isolated source; no production mutation or endurance run.

## Waste and attempt register

The direct numerical test compiles only the production arithmetic module, not
the full 64-column substrate. Full native checks will be bounded and use an
isolated build target. No background monitor, lifetime evidence stream or
population-scale replay is added. Initial sparse-worktree setup needed
`read-tree -mu HEAD` after `--no-checkout`; this was corrected before edits.
Future isolated setup checks a clean index before starting work.

Status: bounded corrections implemented and independently exercised. Six Rust
arithmetic tests and seven Python/native/source checks pass. Full physical
closure remains blocked; no deployment. The producer's averaged fields and
ordinary-property automatic migration were also removed because they are
direct entry paths to the same incorrect field/restore boundary.

Complete findings, impacts, test identities and the remaining integration
contract: [tenth-pass report](A1_ARCLOOM_TENTH_PASS_9c6820200_2026-10-01.md).

Attempt notes: full-file apply_patch uses one Update operation, not Delete/Add
on the same path. The system has no /usr/bin/time; resource measurement uses
Python's standard resource module. Sparse-checkout additions require explicit
git add --sparse. These corrected tool assumptions did not trigger broad
tests or affect production.
