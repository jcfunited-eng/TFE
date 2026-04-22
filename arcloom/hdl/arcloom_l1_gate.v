// ============================================================
// ArcLoom L1 — Gate Formation and Mosaic Projection
// ============================================================
//
// UF-Spec L1: Segments continuous SEV stream into discrete
// episodes (gates) using the boundary operator from L0.
//
// Gate G_k = [t_a, t_b] where D(t) < tau_D throughout.
// On boundary detection, emits gate descriptor:
//   TVR_k = (T_k, V_k, R_k)
//   C_k   = mosaic divergence (count of distinct lattice projections)
//
// Volume integration: rectangular rule over canonical samples.
//   V_k = SUM_t ( beta1*|dF| + beta2*sigma + beta3*kappa )
//
// Mosaic projection: 3 lattices with power-of-2 spacings.
//   P_l(G_k) = (floor(T/h1_l), floor(V/h2_l), floor(R/h3_l))
//   C_k = |{P_0, P_1, P_2}|  (count distinct triplets)
//
// All arithmetic: unsigned 16.16 fixed-point.
// Target: PYNQ-Z2 (Zynq-7020)
// ============================================================

module arcloom_l1_gate #(
    // Volume integration coefficients (16.16 fixed-point)
    parameter BETA1 = 32'h00010000,  // 1.0
    parameter BETA2 = 32'h00010000,  // 1.0
    parameter BETA3 = 32'h00010000,  // 1.0
    parameter MIN_GATE_LEN = 4,      // suppress gates shorter than this

    // Lattice shift amounts for mosaic projection
    // Coarse lattice (large bins)
    parameter L0_T_SH = 4, parameter L0_V_SH = 4, parameter L0_R_SH = 4,
    // Medium lattice
    parameter L1_T_SH = 3, parameter L1_V_SH = 3, parameter L1_R_SH = 3,
    // Fine lattice (small bins)
    parameter L2_T_SH = 2, parameter L2_V_SH = 2, parameter L2_R_SH = 2
)(
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,       // per-sample valid from L0
    input  wire [31:0] abs_dF,         // |delta_F| unsigned 16.16
    input  wire [31:0] sigma,          // sigma unsigned 16.16
    input  wire [31:0] kappa,          // kappa unsigned 16.16
    input  wire        boundary_in,    // D(t) >= tau_D from L0
    input  wire        N_in,           // negative space indicator from L0

    output reg         valid_out,      // pulse: gate descriptor ready
    output reg  [31:0] T_k,           // gate duration (16.16, integer in upper half)
    output reg  [31:0] V_k,           // structural volume (16.16)
    output reg  [31:0] R_k,           // accumulated relevance (16.16)
    output reg  [3:0]  C_k,           // mosaic divergence count
    output reg  [15:0] N_sum_out,     // count of N=1 samples in gate
    output reg  [15:0] T_count_out,   // raw sample count (integer)
    output reg  [31:0] dF_max_out,    // max |dF| in gate (for L2 contrast)
    output reg  [31:0] dF_min_out     // min |dF| in gate (for L2 contrast)
);

    // ---- Internal state ----
    reg        in_gate;
    reg [15:0] t_count;
    reg [31:0] v_accum;
    reg [31:0] r_accum;
    reg [15:0] n_count;
    reg [31:0] df_max;
    reg [31:0] df_min;

    // ---- Volume per sample: beta1*|dF| + beta2*sigma + beta3*kappa ----
    wire [63:0] vt1_full, vt2_full, vt3_full;
    wire [31:0] vt1, vt2, vt3, v_sample;

    assign vt1_full = BETA1 * abs_dF;
    assign vt2_full = BETA2 * sigma;
    assign vt3_full = BETA3 * kappa;
    assign vt1 = vt1_full[47:16];
    assign vt2 = vt2_full[47:16];
    assign vt3 = vt3_full[47:16];
    assign v_sample = vt1 + vt2 + vt3;

    // Saturating volume accumulator
    wire [32:0] v_next_wide;
    wire [31:0] v_next;
    assign v_next_wide = {1'b0, v_accum} + {1'b0, v_sample};
    assign v_next = v_next_wide[32] ? 32'hFFFFFFFF : v_next_wide[31:0];

    // ---- Mosaic projections (combinational from current accumulators) ----
    // Each projection is a triplet of 8-bit integers
    wire [7:0] p0_t, p0_v, p0_r;  // coarse lattice
    wire [7:0] p1_t, p1_v, p1_r;  // medium lattice
    wire [7:0] p2_t, p2_v, p2_r;  // fine lattice

    // Saturating shift: if result > 255, clamp to 255
    wire [15:0] p0_t_raw = t_count >> L0_T_SH;
    wire [15:0] p0_v_raw = v_accum[31:16] >> L0_V_SH;
    wire [15:0] p0_r_raw = r_accum[31:16] >> L0_R_SH;
    assign p0_t = (p0_t_raw > 16'd255) ? 8'd255 : p0_t_raw[7:0];
    assign p0_v = (p0_v_raw > 16'd255) ? 8'd255 : p0_v_raw[7:0];
    assign p0_r = (p0_r_raw > 16'd255) ? 8'd255 : p0_r_raw[7:0];

    wire [15:0] p1_t_raw = t_count >> L1_T_SH;
    wire [15:0] p1_v_raw = v_accum[31:16] >> L1_V_SH;
    wire [15:0] p1_r_raw = r_accum[31:16] >> L1_R_SH;
    assign p1_t = (p1_t_raw > 16'd255) ? 8'd255 : p1_t_raw[7:0];
    assign p1_v = (p1_v_raw > 16'd255) ? 8'd255 : p1_v_raw[7:0];
    assign p1_r = (p1_r_raw > 16'd255) ? 8'd255 : p1_r_raw[7:0];

    wire [15:0] p2_t_raw = t_count >> L2_T_SH;
    wire [15:0] p2_v_raw = v_accum[31:16] >> L2_V_SH;
    wire [15:0] p2_r_raw = r_accum[31:16] >> L2_R_SH;
    assign p2_t = (p2_t_raw > 16'd255) ? 8'd255 : p2_t_raw[7:0];
    assign p2_v = (p2_v_raw > 16'd255) ? 8'd255 : p2_v_raw[7:0];
    assign p2_r = (p2_r_raw > 16'd255) ? 8'd255 : p2_r_raw[7:0];

    // Pairwise triplet comparison
    wire match_01 = (p0_t == p1_t) & (p0_v == p1_v) & (p0_r == p1_r);
    wire match_02 = (p0_t == p2_t) & (p0_v == p2_v) & (p0_r == p2_r);
    wire match_12 = (p1_t == p2_t) & (p1_v == p2_v) & (p1_r == p2_r);

    // Count distinct projections: |{P0, P1, P2}|
    wire [3:0] c_val;
    assign c_val = (match_01 & match_02) ? 4'd1 :        // all same
                   (~match_01 & ~match_02 & ~match_12) ? 4'd3 : // all different
                   4'd2;                                   // exactly one pair matches

    // ---- Gate accumulation FSM ----
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            in_gate     <= 1'b0;
            t_count     <= 16'd0;
            v_accum     <= 32'd0;
            r_accum     <= 32'd0;
            n_count     <= 16'd0;
            df_max      <= 32'd0;
            df_min      <= 32'hFFFFFFFF;
            valid_out   <= 1'b0;
            T_k         <= 32'd0;
            V_k         <= 32'd0;
            R_k         <= 32'd0;
            C_k         <= 4'd1;
            N_sum_out   <= 16'd0;
            T_count_out <= 16'd0;
            dF_max_out  <= 32'd0;
            dF_min_out  <= 32'd0;
        end else begin
            valid_out <= 1'b0;

            if (valid_in) begin
                if (!boundary_in) begin
                    // ---- Inside gate: accumulate ----
                    if (!in_gate) begin
                        // Start new gate
                        in_gate  <= 1'b1;
                        t_count  <= 16'd1;
                        v_accum  <= v_sample;
                        r_accum  <= 32'h00010000;  // r(t) = 1.0 per sample
                        n_count  <= {15'd0, N_in};
                        df_max   <= abs_dF;
                        df_min   <= abs_dF;
                    end else begin
                        // Continue gate
                        t_count  <= t_count + 16'd1;
                        v_accum  <= v_next;
                        r_accum  <= r_accum + 32'h00010000;
                        n_count  <= n_count + {15'd0, N_in};
                        df_max   <= (abs_dF > df_max) ? abs_dF : df_max;
                        df_min   <= (abs_dF < df_min) ? abs_dF : df_min;
                    end
                end else if (in_gate) begin
                    // ---- Boundary: close gate ----
                    if (t_count >= MIN_GATE_LEN) begin
                        valid_out   <= 1'b1;
                        T_k         <= {t_count, 16'd0};  // count -> 16.16
                        V_k         <= v_accum;
                        R_k         <= r_accum;
                        C_k         <= c_val;
                        N_sum_out   <= n_count;
                        T_count_out <= t_count;
                        dF_max_out  <= df_max;
                        dF_min_out  <= df_min;
                    end
                    // Reset accumulators
                    in_gate  <= 1'b0;
                    t_count  <= 16'd0;
                    v_accum  <= 32'd0;
                    r_accum  <= 32'd0;
                    n_count  <= 16'd0;
                    df_max   <= 32'd0;
                    df_min   <= 32'hFFFFFFFF;
                end
                // else: boundary_in && !in_gate -> between gates, skip
            end
        end
    end

endmodule
