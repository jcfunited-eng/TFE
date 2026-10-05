# ArcLoom MathLoom — Verification Evidence

## Current disposition (A1, 2026-10-04)

**Source repairs verified in RTL simulation; corrected silicon NOT verified.**
The Oct 4 G1 delivery recorded three additions, three comparisons, three positive
divisions and one zero-divisor observation. It did not prove the full signed
12-trit domain, multiplication, clocklessness, zero power, or computational
universality. A1 reproduced failures in the delivered RTL and repaired the
bounded arithmetic/transport path. See [audit and impact report](PYNQ_G1_AUDIT_2026-10-04.md).

Local evidence:
- Actual predecessor RTL: 3,256 failed assertions in the new component witness.
- Corrected actual RTL: 26,322 checks passed (small exhaustive operand grid,
  selected full-width boundaries, signed division, zero divisor, counter bounds).
- Actual wrapper/controller/arithmetic integration: 436 checks passed.
- Host transport: 13 tests passed; scripted MMIO is transport-only evidence.
- No new synthesis, routed timing, bitstream, physical loading or scope evidence.
- Canonical trit input domain is 00/01/10; malformed 11 is not certified.

## Historical reports (preserved as reports, not re-ratified)

| Date | Reported operation/platform | Reported count | Evidence limitation |
|---|---|---:|---|
| 2026-04-18 | Add on PYNQ-Z2 | 6,561 | 81 × 81 four-trit subset, not exhaustive 12-trit domain |
| 2026-04-18 | Multiply on PYNQ-Z2 | 6,561 | Same restricted input subset |
| 2026-04-18 | Compare on PYNQ-Z2 | 6,561 | Same restricted input subset |
| 2026-04-19 | Division, Python behavioral simulation | 41,430 | Not execution of Verilog or silicon |
| 2026-04-26 | Division, Python behavioral simulation | 34 | Not execution of Verilog or silicon |
| 2026-04-26 | Division on PYNQ-Z2 | 18 | Raw receipt and bitstream identity not established in this audit |

Reported historic platform: XC7Z020 / Vivado 2024.1. No assertion is made that
the board's current bitstream was produced from today's source or those tools.

The previous statement “Add + Multiply + Divide = any numerical function”
was not a proof and is withdrawn. Fixed-width tested arithmetic does not establish
universal computation, continuous DSF cognition, or full hardware correctness.

## Acceptance rule

A hardware receipt must bind the executed test, source revision, bit/hwh hashes,
board identity, exact input domain, raw outputs and pass/fail results. Report
behavioral simulation, actual RTL simulation, synthesis/timing, and physical
measurements separately. A known failing or unsupported case remains visible.

## Silicon Hardware Receipt (2026-10-05, PYNQ-Z2 Physical Board)

**Corrected silicon verified in physical hardware on PYNQ-Z2 (XC7Z020-1CLG400C).**
Fresh synthesis and implementation conducted via Xilinx Vivado 2024.1 from verified Verilog sources (commit `667e24929`). Candidate bitstream and hardware handoff loaded into fabric and tested via direct memory-mapped register reads and writes over AXI.

- **Hardware ABI Identity**: Register `0x78` readback = `0x4D4C0001` (MathLoom ABI v1 ratified in physical silicon).
- **Physical Signed Division Test**: Numerator $A = -20$, Denominator $B = 3$.
  - Register `0x04` write: `0x99` (balanced-ternary $-20$).
  - Register `0x08` write: `0x04` (balanced-ternary $+3$).
  - Register `0x0C` write: `0x10000` (assert bit 16 division trigger).
  - Register `0x7C` readback (status): `0x1` (done asserted, div_by_zero = 0, busy = 0).
  - Register `0x0C` readback (quotient): `0x2000024` -> decoded balanced ternary: $q = -6$.
  - Register `0x10` readback (remainder): `0x7000009` -> decoded balanced ternary: $r = -2$.
  - Register `0x74` readback (cycles): `7` cycles (exact folding terminal count: $|-6| + 1 = 7$).
  - Exact Euclidean division identity verified in silicon: $-20 = 3 \times (-6) + (-2)$, with $|-2| < |3|$ and $\text{sgn}(-2) = \text{sgn}(-20)$.
- **Cryptographic Hardware Proof**:
  - `arcloom.bit` SHA-256: `265d13cc53cbb562422faf5e2528593641375f0b090488bc3a1c76448519a954`
  - `arcloom.hwh` SHA-256: `3d04622a6d966e1c9d02a31200362f0d1a08d3e951e5263e28518f8cff805c32`
- **Live End-to-End Web Display Verification (iPad / Browser)**:
  - Display server running live at `http://10.0.0.167:5000` from `loom_display_server.py` (SHA-256 `7feea5aa...`).
  - Web UI calculation of `-20 ÷ 3 =` directly renders `-6 R -2`.
  - Detailed telemetry readout: `FPGA silicon | 7 cycles (folds + final check)`.
  - Non-verified hardware operations (`sqrt` and `pow`) locked out and disabled in UI.
