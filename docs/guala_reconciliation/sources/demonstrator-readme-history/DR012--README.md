# ArcLoom component demonstrator

This is a Linux source package for component verification. It is not a
verified autonomous organism, full-field cortical integration, or air-gapped
binary distribution.

## Exact acceptance boundary

- MathLoom preserves finite binary64 values as exact signed rational trits.
- The column model stores all seven fields plus separate global stability
  without converting stored evidence into a physical motor authority.
- A present field, including a present zero field, makes the column step
  refuse BEFORE mutation. Missing typed field-to-material-to-motor coupling
  remains A10, OPEN.
- ArcLoomNeuron is a separate, callable material component with bounded
  numerical integration, exact carrier custody and its own complete codec.
  Its solver is not wired to the column model's motor outputs.
- The component column model still contains authored effector/interlock
  rules. They are NOT evidence of emergent material-neuron motor control.
- ARCLOOM4 restores the accepted complete column state. Rejected experimental
  appended neuron blocks are refused, not discarded or merged with the
  receiving instance. Preserve such bytes; no automatic migration is supplied.
- The matched weight-ablation capability remains A11, OPEN.
  Strict expected failures expose missing capabilities; they do not prove them.

## Contents

Native component sources, exact carrier arithmetic, Python transport,
component console, Verilog source/constraints, and focused verification tests.
The presence of HDL source does not certify FPGA synthesis, timing, or
equivalence to the native material component.

## Build and verify

Use Linux x86_64 with Python 3.11+ (venv/pip), a C toolchain (gcc or clang),
and Rust/Cargo capable of building the supplied Cargo.lock. Native Windows
console execution is not supported. Bootstrap requires network access to
dependencies unless they are already cached; it never installs system packages.

Run from this directory:

```bash
bash setup.sh
.venv/bin/python run_demonstrator.py
```

Setup builds one wheel with Cargo --locked in a fresh directory, installs that
exact wheel in .venv, and verifies the resolved native extension bytes against
the wheel. It does not flatten packages or delete installed module directories.
The printed wheel directory is retained for custody; remove it explicitly
when no longer needed. Direct build/test dependency versions are pinned;
this is not a claim of an offline vendored or reproducible-toolchain release.

The tests report component successes and strict A10/A11 expected failures
separately. A successful setup is NOT sign-off on those capabilities.
No ECS, S3, CloudFront, live state, or deployment operations occur here.

Console controls: b = optical blindout, a = acoustic stimulus,
c = contact input, s = component downscaling routine, q = quit.
These are authored component probes, not autonomous learning evidence.
