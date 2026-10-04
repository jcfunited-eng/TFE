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
