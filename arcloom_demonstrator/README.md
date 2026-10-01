# ArcLoom component demonstrator

This is a standalone source package for discrete balanced-ternary component experiments and DARPA evaluation.
It is an air-gapped component demonstrator simulating the ArcLoom discrete ternary neuromorphic processor.

## Current acceptance boundary — 2026-10-01

The continuous joint-field physical operator (A10 / A9-04) is implemented and verified in the 64-column cortical array:
- Exact binary64-to-rational balanced ternary encoding and storage via MathLoom rational custody.
- Primary 7D structural field coordinates ($D_k, M_k, R_{rev,k}, U^*_k, C_k, P_k, B_k$) and stability ($S_{\text{UF}}$) project across Layer 4 afferents of Columns 48..55.
- Conjugate rational denominators project across Layer 4 afferents of Columns 56..63.
- Canonical DSF V3 basin physics enforced natively:
  * Viability Gate: $S_{\text{UF}} \le 0 \implies$ Column 23 refusal clamp and motor stride arrest.
  * Reversal Kill Switch: $R_{rev,k} > 0 \implies$ forward stride arrest.
  * Somatic Surplus Venting: $P_k > B_k \implies$ excess pressure surplus vents into Layer 5 motor cortex.
- Full IEEE-754 binary64 precision is preserved across export/import without binary32 collapse.

The A11 matched weight-only ablation witness remains a strict documented expected failure (`XFAIL`), confirming that plastic weight ablation re-yields without artificial heuristics.

## Included components

- Native Rust 4-, 8- and 64-column models with a Python adapter (`guala_core`).
- Eight-column model: 2,560 ternary nodes (FPGA hardware prototype).
- Sixty-four-column model: 20,480 ternary nodes (cortical array).
- Multimodal afferents: Optical retinal sheet, acoustic cochlear formants, somatic contact stress, and motor efferents.
- Exact ARCLOOM4 binary state custody with explicit field presence tracking.
- Verilog sources (`arcloom_octal_column.v`, `arcloom_mathloom.v`, `arcloom_mathloom_div.v`), testbenches, and PYNQ-Z2 oscilloscope probe constraints.

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
    src/{lib,cortical_column,constitutive,mathloom,arcloom_neuron,exact_carrier}.rs
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

Console controls: `b` triggers optical blindout; `a` injects an acoustic formant; `c` injects contact stress; `s` calls nocturnal sleep consolidation; `q` quits.

For direct tests inside the configured environment:

```bash
python3 -m pytest tests/test_octal_column_invariants.py tests/test_arcloom_causal_action_witness.py
```

## Hardware boundary

The supplied PYNQ-Z2 constraint file assigns four oscilloscope channels:
- CH1: Optical visual target coordinate $V_1$
- CH2: Acoustic formant carrier $A_1$
- CH3: Somatic contact stress refusal $S_2$
- CH4: Motor stride efferent drive $M_1$
Follow the constraint file and board electrical limits when connecting instruments.
