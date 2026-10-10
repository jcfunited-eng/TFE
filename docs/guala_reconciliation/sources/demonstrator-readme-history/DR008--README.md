# ArcLoom component demonstrator

This is a source package for discrete balanced-ternary component experiments.
It is **not** a certified full-field cognitive organism or a demonstrated
hardware implementation.

## Current acceptance boundary — 2026-10-01

The A10 / A9-04 continuous joint-field physical operator is **unimplemented**.
Exact binary64-to-rational balanced ternary encoding and storage are supported,
but a present field causes the 64-column native transition to raise
`NotImplementedError` before state mutation. The rejected 32-trit cosine/tanh
projection and direct pressure-to-motor injection are absent.

The A11 matched retained-plasticity motor-divergence witness is also open.
Both capabilities remain strict expected failures in the causal witness suite;
an expected failure is not proof of the capability. Passing trained-versus-fresh,
tract-severing, codec or component-retention tests must not be presented as
matched plasticity causation, full DSF cognition or continuous material physics.

The implemented contact model is dimensionless. Its algebraic return map is
not, by itself, a calibration in pascals, joules, amperes or newtons.
No claim of no forgetting, meaningful speech, autonomy, or full diurnal
consolidation follows from the component tests or the historic burn-in.

## Included components

- Native Rust 4-, 8- and 64-column models with a Python adapter.
- Eight-column model: 2,560 ternary nodes.
- Sixty-four-column model: 20,480 ternary nodes; allocated/contact counts and
  measured execution costs belong to the actual selected configuration.
- Optical and acoustic fixture inputs, somatic/contact input and motor outputs.
- Exact current-format state custody and explicit unsupported-boundary errors.
- Verilog sources, testbenches and PYNQ-Z2 probe constraints.

The console supplies synthetic stimuli; it does not run the home-world organism.
World-transaction proof in the main repository does not become standalone
world-transaction proof merely by copying a component witness.

## Layout

```text
arcloom_demonstrator/
  README.md
  setup.sh
  run_demonstrator.py
  benchmark_octal_substrate.py
  native/guala_core/
    Cargo.toml
    Cargo.lock
    pyproject.toml
    src/{lib,cortical_column,mathloom}.rs
  hdl/
    arcloom_octal_column.v
    arcloom_octal_tb.v
    arcloom_mathloom.v
    arcloom_mathloom_div.v
    constraints/pynq_z2_scope.xdc
  substrate/modular_column_substrate.py
  tests/
    test_octal_column_invariants.py
    test_arcloom_causal_action_witness.py
    fixtures/
```

## Running the component console

From the package directory on a workstation with the required build dependencies:

```bash
bash setup.sh
source .venv/bin/activate
python3 run_demonstrator.py
python3 run_demonstrator.py --columns 64
```

The bootstrap may install dependencies; the archive is not an offline
dependency bundle. No time-to-install or fresh-air-gapped-machine claim is made.

Console controls: B changes the optical fixture; A injects an acoustic fixture;
C injects contact stress; S calls the component consolidation operation; Q quits.
These are operator interventions, not autonomous perception, sleep or cognition.

For direct tests inside the configured environment:

```bash
python3 -m pytest tests/test_octal_column_invariants.py tests/test_arcloom_causal_action_witness.py
```

## Hardware boundary

The supplied PYNQ-Z2 constraint file assigns four scope channels:
optical V1, acoustic A1, somatic S2 and motor M1.
Follow the actual constraint file and board electrical limits when connecting
instruments. No newly measured synthesis utilization, loaded bitstream,
on-board timing or scope capture is delivered by this source correction.
Earlier LUT and latency figures are not sign-off measurements for this archive.

## Release interpretation

Archive acceptance means source payload equality, safe paths and exclusion of
caches/build artifacts. It does not close the unimplemented physics.
Do not remove the expected-failure guards, feed only low-order trits, inject
P-minus-B motor current, or change inputs until a false-positive test passes.
The missing law requires the complete typed field, persistent phase settlement,
physical gate and conductance/material dynamics, real producer participation
and same-organism causal verification.
