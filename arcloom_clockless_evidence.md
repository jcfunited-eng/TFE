# ArcLoom SPPU Decision-Path Clocklessness: Source-Level Evidence

**Date:** 2026-05-29
**Scope:** BSIL-BT output to decision strand output
**Method:** Exhaustive RTL source inspection of every module in the datapath
**Repo:** `/workspaces/Tao_Financial_Engine/arcloom/hdl/`

---

## 1. Decision-Path Module Inventory

The decision path begins at the outputs of BSIL-BT (the clocked sensor encoder) and ends at the three decision strand outputs (`decision_steer`, `decision_speed`, `decision_conf`). The following modules comprise this path:

| # | Module | File | Purpose |
|---|--------|------|---------|
| 1 | `arcloom_sppu` | `arcloom_sppu.v` | Top-level SPPU: packs input trits, instantiates 9 local field computations, produces decision outputs |
| 2 | `arcloom_local_field` | `arcloom_ternary_loom.v` (lines 60-92) | Weighted sum of coupled trits with dead-zone thresholding; produces one output trit per field |
| 3 | `arcloom_l6_tcl` | `arcloom_l6_tcl.v` | Topological constraint layer: counts collapsed trits, computes structural lock. Feeds Krimelack commit trigger only -- not in the steer/speed/conf decision datapath. **Ambiguous inclusion:** L6 observes loom_state and produces `structural_lock`, which gates Krimelack commits but does NOT feed back into the decision outputs. Listed here for completeness. |

**Modules explicitly NOT in the decision path:**

| Module | File | Why excluded |
|--------|------|-------------|
| `arcloom_bsil_bt` | `arcloom_bsil_bt.v` | Upstream of decision path (clocked sensor encoder) |
| `arcloom_bsil` | `arcloom_ternary_loom.v` (lines 104-220) | Legacy 3-trit BSIL, also upstream and clocked |
| `arcloom_krimelack` | `arcloom_krimelack.v` | Memory/feedback path, clocked |
| `arcloom_l0_boundary` / `arcloom_l0_sev` | `arcloom_l0_boundary.v` | UF pipeline layer, clocked, not instantiated in `arcloom_top` decision path |
| `arcloom_l1_gate` | `arcloom_l1_gate.v` | UF pipeline layer, clocked |
| `arcloom_l2_metrics` | `arcloom_l2_metrics.v` | UF pipeline layer, clocked |
| `arcloom_l3_resonance` | `arcloom_l3_resonance.v` | UF pipeline layer, clocked |
| `arcloom_l4_dsf` | `arcloom_l4_dsf.v` | UF pipeline layer, clocked |
| `arcloom_uf_pipeline` | `arcloom_uf_pipeline.v` | Wrapper for L0-L4 chain, clocked, not instantiated by `arcloom_top` |
| `arcloom_mathloom_div` | `arcloom_mathloom_div.v` | Iterative divider, clocked |
| `arcloom_mathloom_array` | `arcloom_mathloom_array.v` | Array processor with state machine, clocked |
| MathLoom combinational modules | `arcloom_mathloom.v`, `arcloom_mathloom_alu.v` | Combinational arithmetic, but not instantiated in the SPPU decision path |

**Note on L0-L4:** These modules exist in the repo as a complete UF kernel pipeline implementation but are NOT instantiated inside `arcloom_top` for the current SPPU decision path. The `arcloom_top` module (in `arcloom_ternary_loom.v`, lines 240-569) instantiates BSIL-BT, then SPPU, then Krimelack, then L6. The UF pipeline (`arcloom_uf_pipeline`) is a separate subsystem. The DSF outputs on `arcloom_top` are hardwired to zero (line 314-317):

```verilog
// arcloom_ternary_loom.v, lines 314-317
assign dsf_safe_mode = 1'b0;
assign dsf_valid = 1'b0;
assign dsf_D = 2'b00;
assign dsf_R_rev = 1'b0;
```

---

## 2. Source-Level Proof of No Clocked Logic

### 2.1 `arcloom_sppu` (arcloom_sppu.v)

**Port list (lines 182-217):**
```verilog
// arcloom_sppu.v, line 182
// NO CLOCK INPUT.

// IR sensor strands (5 x 16 bits = 80 bits)
input  wire [15:0] in_front_dist,
input  wire [15:0] in_front_dir,
input  wire [15:0] in_front_accel,
input  wire [15:0] in_left_dist,
input  wire [15:0] in_right_dist,

// Camera strands (7 x 16 bits = 112 bits)
input  wire [15:0] in_cam_y_upper,
...
input  wire [15:0] in_cam_density,

input  wire [7:0]  familiarity,

input  wire signed [15:0] ext_h_ctx,
input  wire signed [15:0] ext_h_mmtm,
input  wire signed [15:0] ext_h_steer,
input  wire signed [15:0] ext_h_speed,
input  wire signed [15:0] ext_h_conf,

output wire [209:0] loom_state,
output wire [1:0]  decision_steer,
output wire [1:0]  decision_speed,
output wire [1:0]  decision_conf,
output wire signed [31:0] field_ctx_0, field_ctx_1, field_ctx_2,
output wire signed [31:0] field_mmtm_0, field_mmtm_1, field_mmtm_2,
output wire signed [31:0] field_dcsn_0, field_dcsn_1, field_dcsn_2
```

**Clock/reset inputs:** NONE. The port list contains no `clk`, `clock`, `aclk`, `rst_n`, or `reset` signal.

**`always @(posedge ...)` blocks:** NONE. Zero occurrences in the entire file.

**`<=` (non-blocking) assignments:** NONE.

**All logic consists of:**
- `wire` continuous assignments (lines 222-227, 271-273, 296-308)
- Module instantiations of `arcloom_local_field` (lines 234-291)
- Comment line 27: `// NO clock. NO reg. Purely combinational.`

**Verdict: CONFIRMED COMBINATIONAL. No clock port, no sequential logic.**

### 2.2 `arcloom_local_field` (arcloom_ternary_loom.v, lines 60-92)

**Module header (lines 60-70):**
```verilog
module arcloom_local_field #(
    parameter N_INPUTS = 9,
    parameter signed [31:0] DEAD_ZONE = 32'd20
)(
    input  wire [2*N_INPUTS-1:0]  coupled_trits,
    input  wire [16*N_INPUTS-1:0] weights,
    input  wire signed [15:0]     external_h,
    input  wire [7:0]             dead_zone_adj,
    output wire [1:0]             trit_out,
    output wire signed [31:0]     field_value
);
```

**Clock/reset inputs:** NONE. No `clk`, `clock`, or `rst` port.

**`always` block (lines 74-83):**
```verilog
always @(coupled_trits or weights or external_h) begin
    total = {{16{external_h[15]}}, external_h};
    for (i = 0; i < N_INPUTS; i = i + 1) begin
        case (coupled_trits[2*i +: 2])
            2'b01:   total = total + {{16{weights[16*i+15]}}, weights[16*i +: 16]};
            2'b10:   total = total - {{16{weights[16*i+15]}}, weights[16*i +: 16]};
            default: ;
        endcase
    end
end
```

This is an `always @(...)` block with a **combinational sensitivity list** (`coupled_trits or weights or external_h`). There is no `posedge` or `negedge` in the sensitivity list. The variable `total` is declared as `reg signed [31:0]` (line 72), which is required by Verilog syntax for variables assigned inside `always` blocks, but this does NOT imply sequential logic. The `=` (blocking) assignments confirm combinational intent.

**`<=` (non-blocking) assignments:** NONE. All assignments use `=` (blocking).

**Remaining logic (lines 85-92):**
```verilog
wire signed [31:0] effective_dz = DEAD_ZONE + {24'd0, dead_zone_adj};

assign trit_out = (total > effective_dz)  ? 2'b01 :
                  (total < -effective_dz) ? 2'b10 :
                  2'b00;

assign field_value = total;
```

All continuous `assign` statements.

**Verdict: CONFIRMED COMBINATIONAL. No clock port, no posedge, no non-blocking assignments.**

### 2.3 `arcloom_l6_tcl` (arcloom_l6_tcl.v)

**Module header (lines 25-46):**
```verilog
module arcloom_l6_tcl #(
    parameter N_TRITS    = 18,
    parameter KNEE       = 7
)(
    // NO CLOCK. Combinational.
    input  wire [2*N_TRITS-1:0] loom_state,
    input  wire                 disruption_active,
    input  wire                 recovery_pending,
    output wire                 structural_lock,
    output wire [6:0]           n_effective,
    output wire [6:0]           n_collapsed,
    output wire [7:0]           omega
);
```

**Clock/reset inputs:** NONE. Comment on line 33: `// NO CLOCK. Combinational.`

**`always` block (lines 56-62):**
```verilog
always @(loom_state) begin
    collapsed = 7'd0;
    for (t = 0; t < N_TRITS; t = t + 1) begin
        if (loom_state[2*t +: 2] == 2'b01 || loom_state[2*t +: 2] == 2'b10)
            collapsed = collapsed + 7'd1;
    end
end
```

Combinational sensitivity list (`loom_state` only). Blocking assignments only.

**Remaining logic (lines 65-90):** All continuous `assign` statements.

**Verdict: CONFIRMED COMBINATIONAL. No clock port, no posedge, no non-blocking assignments.**

**However:** L6's `structural_lock` output feeds only into Krimelack's `commit_request` input (line 536 of `arcloom_ternary_loom.v`). It does NOT feed back into the SPPU decision outputs. L6 is a combinational observer that gates memory commits, not a participant in the decision computation.

### 2.4 Submodules used by `arcloom_local_field`

`arcloom_local_field` does not instantiate any submodules. Its logic is self-contained: a weighted sum loop and a three-way comparator, both combinational.

The `arcloom_trit` and `arcloom_trit_mult` modules (lines 27-54 of `arcloom_ternary_loom.v`) are defined in the same file but are NOT instantiated by `arcloom_local_field` or `arcloom_sppu`. They are legacy modules from an earlier architecture.

---

## 3. Vivado Synthesis Evidence

**No Vivado synthesis reports (.rpt files) exist in this repository.** A search for `*.rpt`, `*synth*`, and `*utilization*` files found no FPGA synthesis artifacts.

The ASIC architecture spec (`docs/ArcLoom_ASIC_Architecture_v1_0.tex`) describes the SPPU as a "fixed-weight combinational classifier" (line 56) but does not contain post-synthesis resource counts or timing reports.

Without synthesis reports, the clocklessness claim rests entirely on the RTL source analysis above. An independent verification would require running Vivado synthesis and confirming:
1. Zero flip-flops inferred for `arcloom_sppu` and `arcloom_local_field`
2. Zero BRAM usage
3. All paths reported as combinational in timing analysis

---

## 4. Honest Boundary Statement

The clocklessness claim applies ONLY to the decision path from BSIL-BT output to decision strand output. The following components are explicitly clocked and are not subject to this claim:

**Clocked (upstream — sensor I/O boundary):**
- `arcloom_bsil_bt`: BRAM-based balanced ternary encoder with 2-cycle pipeline. Uses `always @(posedge clk)` for ROM read, output registration, and history tracking (lines 124-188 of `arcloom_bsil_bt.v`). 10 instances in `arcloom_top` (3 IR sensors + 7 camera strands).
- `arcloom_bsil`: Legacy 3-trit BSIL with `always @(posedge clk or negedge rst_n)` (line 180 of `arcloom_ternary_loom.v`). Not used in current architecture but defined in the same file.

**Clocked (downstream — feedback/memory):**
- `arcloom_krimelack`: Structural memory with clocked write logic (`always @(posedge clk or negedge rst_n)`, line 106 of `arcloom_krimelack.v`). Recall scoring is combinational, but commit logic is clocked. The `match_score` output feeds back into `arcloom_top`'s familiarity computation, which IS a clocked feedback path (`damped_fam` register, lines 446-461 of `arcloom_ternary_loom.v`).

**Clocked (feedback into SPPU via `arcloom_top`):**
- The `damped_fam` register (line 446) and `speed_bias_with_target` computation (line 471-472) in `arcloom_top` are clocked. These feed into the SPPU's `familiarity` and `ext_h_speed` inputs. The SPPU itself is combinational, but its inputs are driven by clocked logic in `arcloom_top`. This means the SPPU's outputs change combinationally in response to inputs that are updated on clock edges.

**Clocked (present in repo but not in SPPU decision path):**
- `arcloom_l0_boundary`, `arcloom_l0_sev`, `arcloom_l1_gate`, `arcloom_l2_metrics`, `arcloom_l3_resonance`, `arcloom_l4_dsf`: All clocked. These form the UF kernel pipeline (`arcloom_uf_pipeline`), which is NOT instantiated in `arcloom_top`.
- `arcloom_mathloom_div`: Iterative clocked divider.
- `arcloom_mathloom_array`: Clocked array processor with state machine.

**Combinational (present in repo, not in SPPU decision path):**
- `arcloom_mathloom_alu`, `arcloom_bt_fulladder`, `arcloom_bt_adder`, `arcloom_bt_sub`, `arcloom_bt_abs`, `arcloom_bt_compare`, `arcloom_trit_neg`, `arcloom_trit_mul`: All combinational MathLoom arithmetic modules. These are not instantiated in the SPPU.

---

## 5. What This Proves and What It Does Not Prove

### What it proves

The RTL source code for `arcloom_sppu` and its sole dependency `arcloom_local_field` contains zero clock inputs, zero `always @(posedge ...)` blocks, zero non-blocking assignments, and zero register (`reg`) variables used as state elements. Every signal path from the SPPU's 12 input strands (192 bits of packed trits) plus familiarity and external field inputs to its 3 decision outputs (6 bits total) and 210-bit loom state is composed exclusively of combinational logic: weighted sums via blocking-assignment loops and ternary comparators via conditional assigns. The `arcloom_l6_tcl` module, which also operates on loom state, is independently confirmed combinational but does not feed back into the decision outputs.

### What it does not prove

This analysis is limited to RTL source inspection. It does not constitute a formal verification or synthesis proof. Vivado synthesis has not been run in this environment, so there are no post-synthesis timing or resource reports confirming zero flip-flop inference. The SPPU's inputs are driven by clocked registers in `arcloom_top` (BSIL-BT outputs and damped familiarity), meaning the end-to-end system from sensor ADC to motor command IS clocked at its boundaries. The claim is strictly that the decision computation between those boundaries is a single combinational evaluation with no internal state. Additionally, the Krimelack recall path (combinational pattern matching) feeds familiarity back through a clocked damping register in `arcloom_top`, creating a feedback loop that is clocked even though the SPPU evaluation within that loop is not.
