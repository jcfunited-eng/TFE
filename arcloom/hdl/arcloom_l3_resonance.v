// ============================================================
// ArcLoom L3 — Resonance and Contextual Gating
// ============================================================
//
// UF-Spec L3: Computes aggregate resonance (confidence/alignment)
// and applies contextual gating rules.
//
// Resonance vector (5 components):
//   R_vec = (w_k, CV_norm, S_k, 1/(1+C_k), 1-U_k)
//
// Scalar resonance (equal-weight baseline):
//   R(k) = (1/5) * SUM_i R_vec[i]
//
// Hysteresis flag:
//   Hyst_k = 1 iff |R(k) - R(k-1)| > h_max
//
// Contextual gate:
//   g_k = (U_k <= U_max) AND (IAS_k = 0) AND (Hyst_k = 0)
//
// Unified Resonance Field:
//   URF_k = g_k * R(k)
//
// All arithmetic: unsigned 16.16 fixed-point.
// Target: PYNQ-Z2 (Zynq-7020)
// ============================================================

module arcloom_l3_resonance #(
    parameter H_MAX = 32'h00005000,   // 0.3125 — hysteresis threshold
    parameter U_MAX = 32'h0000D99A,   // 0.85 — uncertainty gate threshold
    // 1/5 = 0.2 in 16.16
    parameter INV_5 = 32'h00003333
)(
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] w_k,           // weight from L2
    input  wire [31:0] CV_norm,       // contrast from L2
    input  wire [31:0] S_k,           // score from L2
    input  wire [31:0] U_k,           // uncertainty from L2
    input  wire        IAS_k,         // anomaly flag from L2
    input  wire [3:0]  C_k,           // mosaic divergence from L2

    output reg         valid_out,
    output reg  [31:0] R_scalar,      // scalar resonance R(k) in [0,1]
    output reg  [31:0] URF_k,         // unified resonance field in [0,1]
    output reg         g_k,           // contextual gate (1 = pass)
    output reg         Hyst_k,        // hysteresis flag
    // Pass-throughs for L4
    output reg  [31:0] U_k_out,
    output reg         IAS_k_out,
    output reg  [3:0]  C_k_out
);

    localparam [31:0] ONE = 32'h00010000;  // 1.0 in 16.16

    // ---- 1/(1+C_k) lookup table ----
    // C_k is small integer (1-3 for 3 lattices, up to 8 max)
    reg [31:0] inv_1_plus_c;
    always @(*) begin
        case (C_k)
            4'd0:    inv_1_plus_c = ONE;           // 1/(1+0) = 1.0
            4'd1:    inv_1_plus_c = 32'h00008000;  // 1/2 = 0.5
            4'd2:    inv_1_plus_c = 32'h00005555;  // 1/3 = 0.333
            4'd3:    inv_1_plus_c = 32'h00004000;  // 1/4 = 0.25
            4'd4:    inv_1_plus_c = 32'h00003333;  // 1/5 = 0.2
            4'd5:    inv_1_plus_c = 32'h00002AAA;  // 1/6 = 0.167
            4'd6:    inv_1_plus_c = 32'h00002492;  // 1/7 = 0.143
            4'd7:    inv_1_plus_c = 32'h00002000;  // 1/8 = 0.125
            default: inv_1_plus_c = 32'h00001C71;  // 1/9 = 0.111
        endcase
    end

    // ---- Resonance vector components ----
    wire [31:0] rv_0 = w_k;                                  // weight
    wire [31:0] rv_1 = CV_norm;                              // contrast
    wire [31:0] rv_2 = S_k;                                  // score
    wire [31:0] rv_3 = inv_1_plus_c;                         // 1/(1+C)
    wire [31:0] rv_4 = (U_k <= ONE) ? (ONE - U_k) : 32'd0;  // 1 - U_k

    // ---- Scalar resonance: R(k) = (1/5) * sum(R_vec) ----
    wire [31:0] rv_sum = rv_0 + rv_1 + rv_2 + rv_3 + rv_4;
    wire [63:0] r_prod = INV_5 * rv_sum;
    wire [31:0] r_raw  = r_prod[47:16];
    wire [31:0] r_clamped = (r_raw > ONE) ? ONE : r_raw;

    // ---- Hysteresis detection ----
    reg [31:0] R_prev;  // R(k-1)

    wire [31:0] r_diff = (r_clamped >= R_prev) ?
                         (r_clamped - R_prev) :
                         (R_prev - r_clamped);
    wire hyst_flag = (r_diff > H_MAX);

    // ---- Contextual gate ----
    wire gate_pass = (U_k <= U_MAX) & (~IAS_k) & (~hyst_flag);

    // ---- URF ----
    wire [31:0] urf_val = gate_pass ? r_clamped : 32'd0;

    // ---- Register outputs ----
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid_out  <= 1'b0;
            R_scalar   <= 32'd0;
            URF_k      <= 32'd0;
            g_k        <= 1'b0;
            Hyst_k     <= 1'b0;
            R_prev     <= 32'd0;
            U_k_out    <= 32'd0;
            IAS_k_out  <= 1'b0;
            C_k_out    <= 4'd1;
        end else begin
            valid_out <= valid_in;
            if (valid_in) begin
                R_scalar  <= r_clamped;
                URF_k     <= urf_val;
                g_k       <= gate_pass;
                Hyst_k    <= hyst_flag;
                R_prev    <= r_clamped;  // store for next gate
                // Pass-throughs
                U_k_out   <= U_k;
                IAS_k_out <= IAS_k;
                C_k_out   <= C_k;
            end
        end
    end

endmodule
