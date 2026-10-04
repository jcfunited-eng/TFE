# PYNQ-G1-AUDIT-01 — audit and bounded source repairs

## Disposition

G1's latest reports are **not accepted as comprehensive hardware proofs**.
Concrete arithmetic and register-I/O defects are repaired locally and tested.
The board's loaded image has not been changed or independently identified.

Delivery commits audited: `7bb8f4649998bc6fb6ddb1d6dd1a8c53978d83dd`
and `211f7952dbc38fca29c89d2608e964f61d618be4`. Both changed documentation,
not hardware source. All code conclusions below refer to inspected source;
matching that source to the actual board remains unproved.

Architecture gate: requested exact component arithmetic and truthful physical
evidence; current code contains a clocked legacy sensor/motor controller, not
full DSF cognition. Conflict: **yes** with the reports' broader claims. No
extension of scalar steering/familiarity policy, no kernel modifications, no
A10/A11 closure. This is a reduced component audit, missing the canonical joint
seven-field neuronal/organism path. The next item is board-bound verification
of a correctly built, pin-compatible candidate—not another broad audit loop.

## Findings, exact repairs, incoming and outgoing dependencies

| Finding | Correction | Incoming → affected implementation → outgoing impact |
|---|---|---|
| P1: first G1 commit deleted 23,941 ledger lines | Restored exact 2,826,294-byte historical ledger from `968431dd6`, retaining later entries | Prior Git blob → `collaborative_todo.md` → all project handoffs; no historic claim re-ratified |
| P2: absolute value reads only allocated top trit | Determine sign from highest **nonzero** trit | Canonical input → `arcloom_bt_abs` in `arcloom_mathloom.v` → signed divider and standalone mirror |
| P3: signed division folds signed operands directly | Fold positive magnitudes, restore quotient/remainder signs | `abs`/subtract/compare/add → `arcloom_mathloom_div.v` → AXI wrapper and unused array caller; mirror synchronized |
| P4: cycle count overflows at 18 bits and is truncated again to 8 | Widen to 19; preserve legacy low-byte read, expose complete count at `0x74` | Divider → wrapper latch/readback → corrected calculator; array wire width only |
| P5: stale READY, ambiguous product/done bits, stale zero-divisor cycles | Dedicated status `0x7C`, clear completion on new work, zero DBZ counter, pending ownership | Trigger/operand writes → divider and wrapper → host completion acceptance |
| P6: AXI write depends on coincident address/data; reads can acknowledge without accepting | Independently capture AW/W, retain responses under backpressure; reject partial writes with SLVERR | AXI master → wrapper → all register consumers, including motor-enable register; motor equations unchanged |
| P7: console loses addition carry and accepts unready division | Decode all 13 sum trits; poll dedicated status; use full count; serialize complete calculator transaction | `/api/calc` → exact MMIO in `loom_display_server.py` → calculator UI; no substitute software result |
| P8: console can silently treat old bitstream as repaired | Require identity `0x4D4C0001` at `0x78` before arithmetic writes | Loaded image → transport ABI guard → old image returns explicit error, not a false pass |
| P9: inaccurate flags and displayed evidence | Correct compare documentation, structural-lock/safe-mode and match-score bit positions; label cycles accurately; supply missing capture-status DOM node | Wrapper bit packing → console decoding/UI → observer only; no steering-policy modification |
| P10: blanket silicon/clockless/completeness claims exceed evidence | Correct verification log and ledger; retain G1 observations as attributed reports | Historical claims → audit record → no DARPA hardware sign-off from software checks |

### Exact arithmetic contract

For canonical 12-trit inputs, `T = (3^12 - 1)/2 = 265720`.

For nonzero B:

```
m = floor(|A| / |B|)
q = sign(A) * sign(B) * m
r = sign(A) * (|A| - m*|B|)
A = B*q + r; |r| < |B|
cycle_count = m + 1 <= 265721
counter_width = ceil(log2(265722)) = 19
```

The extra counted cycle is the **terminal comparison**, not setup. B=0 returns
q=0, r=A, DBZ=1, done=1, cycles=0. A start while the divider is running does not
replace the active operands. Wrapper writes to arithmetic operands/start while
pending are refused; reset cancels pending work. No floating approximation.

Addition preserves `A+B = decode(sum12) + decode(carry)*3^12`. Products retain
all 24 trits. Invalid `11` encodings are rejected by the host decoder; the RTL
certification domain remains canonical trits, not malformed-input behavior.

### Host changes and compatibility impact

The calculator requires the new ABI and a single software writer. Its lock
serializes requests within this server; it cannot arbitrate another notebook
or process writing the same hardware. A one-second I/O watchdog and finite
poll bound reject missing completion; neither defines physical dynamics.
Independent integer identities validate hardware receipts but never replace a
bad hardware answer with a software answer.

The old composed `pow` and `sqrt` routes were software-orchestrated loops, not
standalone hardware primitives. Their unverified routes/buttons now explicitly
refuse/disable operation rather than advertise `hardware=True`. They are not
claimed repaired or certified. Basic add/subtract/multiply/compare/divide remain
the bounded hardware contract.

The server's existing top-level overlay loading and camera initialization are
not run in this audit. This is not a general server security or camera-retirement
approval. Do not launch it on the robot merely to run host tests.

## Hardware claims that remain unproved

The source causal chain is:

`XADC → clocked BSIL ROM/registers → combinational SPPU → clocked decision registers → motor gate`.

Thus a combinational sub-block does not make the end-to-end robot clockless.
Disable drives RTL logical zero; neither measured 0 mV nor zero standby supply
power follows. Physical delay, voltage and supply-current claims require
separate measurements. No scope traces, bit/hwh hashes or routed timing reports
were attached to these delivery commits.

For aligned samples and the stated side baselines, the existing source computes:

`steer = clamp(L-111,0,3280) - clamp(R-144,0,3280)`.

At L=265/R=268 this is +30, not the reported +47. The ADC and field reads are
not an atomic same-sample receipt; this discrepancy does not alone identify a
silicon fault. The decision threshold is `250 + active_familiarity`, not always
250. Samples +248 and +320 only bracket a transition, not a one-count threshold.
The processor can also write baselines, familiarity and commit requests, so
“PS only polls/interlocks” is too broad.

`dsf_valid` is tied to zero in this legacy top. Scalar steering thresholds and
stored familiarity are not evidence of the canonical seven-field mechanism.
The BSIL path still saturates to eight trits and has derivative-width/pipeline
concerns; the XADC reader includes filtering. Nothing here certifies lossless
raw transduction or fixes that architecture by renaming it.

The unused array processor is not instantiated in the audited board wrapper.
Only its divider counter wire was widened. Its six-bit 1–64 length contract,
MEAN counter use, SUB_SCALAR staging and truncated SUM_SQ/accumulation need a
separate width/operation repair if it is ever mounted. No array pass is claimed.

## Executed verification

| Evidence | Result | What it does not establish |
|---|---|---|
| `tb_mathloom_exact.v` against predecessor | 3,256 failures / 26,313 reached checks | Broad pass claims are falsified; no physical failure inferred without image identity |
| Same bench against repaired arithmetic | 26,322 checks passed | Selected 12-trit boundaries plus exhaustive `[-40,40]^2`, not exhaustive full 12-trit pairs |
| `tb_mathloom_axi.v`, actual wrapper/top/dependencies | 436 checks passed | RTL simulation, not AXI electrical timing or on-board motor measurements |
| `test_mathloom_transport.py` | 13 tests passed; all 531,441 legal input integers round-trip through transport encoding | Scripted MMIO checks only; not hardware evidence |
| Primary/mirror source hashes | Identical arithmetic primitives and divider | Release archive not rebuilt or certified |
| Restored ledger prefix | SHA-256 matches historical Git blob exactly | Restored statements remain historical |

The AXI bench covers address-before-data and data-before-address, held read/write
responses, partial-write refusal, full-word motor enable/disable register
semantics, signed results, count beyond 255, same-operands retrigger, refused busy writes, reset during
division and DBZ. The motor-enable-off equations produce four logic zeros in
simulation; no robot actuation was performed.

Source `git diff --check` is clean. The restored historical ledger contains
nine pre-existing trailing-whitespace findings; they are preserved to maintain
the byte-identical historical prefix, not concealed as a clean diff.

### Reproduction (repository root; Icarus Verilog and Python required)

Use a new temporary output directory, not a shared store. Commands do not load
PYNQ, run a server, or contact production.

```bash
audit_tmp=$(mktemp -d /tmp/arcloom-mathloom-check.XXXXXX)
iverilog -g2012 -s tb_mathloom_exact -o "$audit_tmp/exact" arcloom/hdl/arcloom_mathloom.v arcloom/hdl/arcloom_mathloom_alu.v arcloom/hdl/arcloom_mathloom_div.v arcloom/sim/tb_mathloom_exact.v
timeout 45s vvp "$audit_tmp/exact"
iverilog -g2012 -s tb_mathloom_axi -o "$audit_tmp/axi" arcloom/sim/tb_mathloom_axi.v arcloom/hdl/arcloom_axi_wrapper.v arcloom/hdl/arcloom_mathloom.v arcloom/hdl/arcloom_mathloom_alu.v arcloom/hdl/arcloom_mathloom_div.v arcloom/hdl/arcloom_ternary_loom.v arcloom/hdl/arcloom_bsil_bt.v arcloom/hdl/arcloom_sppu.v arcloom/hdl/arcloom_krimelack.v arcloom/hdl/arcloom_l6_tcl.v
timeout 30s vvp "$audit_tmp/axi"
timeout 30s python -m unittest discover -s arcloom/sim -p test_mathloom_transport.py -v
```

### Candidate identity (SHA-256)

```
988deb22e0117b69765943e50c0a5d7a9075cd35588e8b41646dfcb863fc463e  arcloom/hdl/arcloom_mathloom.v
8b97541f3217cf63a296b492c90c8db235f2ca18e8de8ef8ebf38cfe23596657  arcloom/hdl/arcloom_mathloom_div.v
ab87c6b49bf93171112656f8f6a2f9702594470ce0e0f28962f92552eb27fdbb  arcloom/hdl/arcloom_axi_wrapper.v
7feea5aabd84a254b9584250f41afe435924304b0f863d456e81554249d987aa  arcloom/notebooks/loom_display_server.py
d50920c45f7b17ad254a901f0734a317076601ab383eee1237658de99af49505  restored historical ledger prefix (2826294 bytes)
```

## Single next implementation item for G1

Produce the **board-bound candidate verification receipt**: preserve/hash the
currently loaded bit/hwh first; build these sources with the actual robot's
verified pin constraints; retain synthesis/utilization/timing and bit/hwh
hashes; repeat the signed, carry, long-counter, readiness and gate-off cases
on the board with motors safely disabled. The newer scope constraints reuse
motor Pmod pins and must not be substituted blindly. No claim of new silicon
delivery, fully clockless operation or zero standby power is authorized by
this source audit.
