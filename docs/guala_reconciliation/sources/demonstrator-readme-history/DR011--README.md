# ArcLoom component demonstrator

This is a standalone source package for discrete balanced-ternary component experiments and DARPA evaluation.
It simulates the ArcLoom discrete ternary neuromorphic processor substrate.

## Current acceptance boundary — 2026-10-01

- Exact binary64-to-rational balanced ternary encoding and storage via MathLoom rational custody.
- Primary 7D structural field coordinates ($D_k, M_k, R_{rev,k}, U^*_k, C_k, P_k, B_k$) and stability ($S_{\text{UF}}$) project directly across Layer 4 afferents of Columns 48..55 without modulo folding or double-sign inversion.
- Conjugate rational denominators project across Layer 4 afferents of Columns 56..63.
- Layer 4 capacity is bounded at 64 ternary digits per column. Field incidence at positions $\ge 64$ triggers strict atomic fail-closed refusal before mutation, preserving information conservation.
- The microscopic material neuron operator (`ArcLoomNeuronState`, `ArcLoomTransitionOperator`) is integrated into `ModularSubstrate64D` across 14 canonical typed fabric edges coupling field dimensions to the 4-phase manifold.
- Motor stride and Column 23 barrier refusal causally emerge from continuum contact yield stress mechanics ($f = |\sigma| - Y \le 0$). Direct software bypass clamps have been removed.
- All operative material neuron state (phase positions, velocities, contact geometry, plastic offsets, ion reservoirs, and work accounting) is persisted directly in canonical ARCLOOM4 binary checkpoints.
- A functioning component console is provided. Full multi-column continuous field integration and the A11 matched weight-only ablation witness remain strict documented expected failure / refusal gates (`XFAIL` / `NotImplementedError`), maintaining ground-truth DARPA boundary compliance.

## Included components

- Native Rust 4-, 8- and 64-column macroscopic models with a Python adapter (`guala_core`).
- Microscopic continuum material neuron (`ArcLoomNeuron`) with integer charge custody (`exact_carrier`).
- Eight-column model: 2,560 ternary nodes (FPGA hardware prototype).
- Sixty-four-column model: 20,480 ternary nodes (cortical array).
- Multimodal afferents: Optical retinal sheet, acoustic cochlear formants, somatic contact stress, and motor efferents.
- Exact ARCLOOM4 binary state custody with explicit field presence tracking.
- Verilog sources (`arcloom_octal_column.v`, `arcloom_mathloom.v`, `arcloom_mathloom_div.v`), testbenches, and PYNQ-Z2 oscilloscope probe constraints.

## Platform requirements

- Supported host OS: Linux x86_64 with POSIX terminal (termios/tty support for interactive controls). Native Windows execution is not supported.
- Build prerequisites: Python 3.10+ (with venv and pip), Rust/Cargo 1.75+, and standard C build tools (gcc/clang).
- Note: This is a standalone SOURCE distribution that compiles native extensions locally via `setup.sh`. It requires network access during bootstrap to download build tools and dependencies unless pre-installed.

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
    src/{lib,cortical_column,mathloom,arcloom_neuron,exact_carrier}.rs
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
    test_arcloom_engineered_neuron.py
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

Console controls: `b` triggers optical blindout; `a` injects an acoustic formant; `c` injects contact stress; `s` calls nocturnal sleep consolidation; `q` quits.

For direct tests inside the configured environment:

```bash
python3 -m pytest tests/test_octal_column_invariants.py tests/test_arcloom_causal_action_witness.py tests/test_arcloom_engineered_neuron.py
```

## Hardware boundary

The supplied PYNQ-Z2 constraint file assigns four oscilloscope channels:
- CH1: Optical visual target coordinate $V_1$
- CH2: Acoustic formant carrier $A_1$
- CH3: Somatic contact stress refusal $S_2$
- CH4: Motor stride efferent drive $M_1$
Follow the constraint file and board electrical limits when connecting instruments.
