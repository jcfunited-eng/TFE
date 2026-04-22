// ============================================================
// ArcLoom L2 — Interpretive Metrics
// ============================================================
//
// UF-Spec L2: Computes per-gate structural assessment.
//
//   w_k    = weight (salience) in [0,1]
//   CV_k   = contrast (internal diversity) in [0,1]
//   S_k    = score (regime quality) in [0,1]
//   U_k    = uncertainty in [0,1]
//   IAS_k  = anomaly suppression flag {0,1}
//
// Uncertainty functional (UF-Spec normative):
//   U_k = lambda1*(C_k-1)/(L-1) + lambda2*(delta_g/delta_max) + lambda3*N_gate
//
// Implementation choices (spec-compliant, implementation-defined):
//   w_k    = clamp(V_k >> W_SHIFT, 1.0)   — volume-normalized salience
//   CV_k   = clamp((dF_max - dF_min) >> CV_SHIFT, 1.0)
//   S_k    = w_k                           — salience-based quality
//   delta_g = CV_k (contrast as divergence proxy)
//   N_gate = majority flag: 2*N_sum >= T_count
//
// All arithmetic: unsigned 16.16 fixed-point.
// Target: PYNQ-Z2 (Zynq-7020)
// ============================================================

module arcloom_l2_metrics #(
    parameter W_SHIFT    = 8,             // V_k >> W_SHIFT for weight normalization
    parameter CV_SHIFT   = 8,             // dF_range >> CV_SHIFT for contrast
    parameter LAMBDA1    = 32'h00006666,  // 0.4 — mosaic divergence weight
    parameter LAMBDA2    = 32'h00004CCC,  // 0.3 — gate divergence weight
    parameter LAMBDA3    = 32'h00004CCC,  // 0.3 — negative space weight
    parameter U_ANOMALY  = 32'h0000E666,  // 0.9 — IAS threshold
    parameter U_MAX      = 32'h0000D99A   // 0.85 — hardening threshold (passed to L3)
)(
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] V_k,           // structural volume from L1
    input  wire [3:0]  C_k,           // mosaic divergence from L1
    input  wire [15:0] N_sum,         // negative space count from L1
    input  wire [15:0] T_count,       // sample count from L1
    input  wire [31:0] dF_max,        // max |dF| in gate from L1
    input  wire [31:0] dF_min,        // min |dF| in gate from L1

    output reg         valid_out,
    output reg  [31:0] w_k,           // weight in [0,1]
    output reg  [31:0] CV_norm,       // contrast in [0,1]
    output reg  [31:0] S_k,           // score in [0,1]
    output reg  [31:0] U_k,           // uncertainty in [0,1]
    output reg         IAS_k,         // anomaly suppression flag
    output reg  [3:0]  C_k_out        // pass-through for downstream
);

    localparam [31:0] ONE = 32'h00010000;  // 1.0 in 16.16

    // ---- Weight: salience from volume ----
    wire [31:0] w_raw = V_k >> W_SHIFT;
    wire [31:0] w_clamped = (w_raw > ONE) ? ONE : w_raw;

    // ---- Contrast: range of |dF| within gate ----
    wire [31:0] dF_range = (dF_max >= dF_min) ? (dF_max - dF_min) : 32'd0;
    wire [31:0] cv_raw = dF_range >> CV_SHIFT;
    wire [31:0] cv_clamped = (cv_raw > ONE) ? ONE : cv_raw;

    // ---- Negative space majority flag ----
    // N_gate = 1 if more than half of samples had N=1
    wire n_majority = ({1'b0, N_sum, 1'b0} >= {2'b00, T_count});

    // ---- Uncertainty: U_k = L1*(C-1)/(L-1) + L2*CV + L3*N_gate ----

    // Term 1: lambda1 * (C_k-1)/(L-1) with L=3 lattices
    // C=1: 0, C=2: lambda1*0.5, C>=3: lambda1*1.0
    wire [31:0] u_term1;
    assign u_term1 = (C_k <= 4'd1) ? 32'd0 :
                     (C_k == 4'd2) ? (LAMBDA1 >> 1) :
                     LAMBDA1;

    // Term 2: lambda2 * CV_norm (contrast as divergence proxy)
    wire [63:0] u_t2_full;
    wire [31:0] u_term2;
    assign u_t2_full = LAMBDA2 * cv_clamped;
    assign u_term2 = u_t2_full[47:16];

    // Term 3: lambda3 * N_gate (binary: 0 or lambda3)
    wire [31:0] u_term3 = n_majority ? LAMBDA3 : 32'd0;

    // Sum and clamp
    wire [31:0] u_sum = u_term1 + u_term2 + u_term3;
    wire [31:0] u_clamped = (u_sum > ONE) ? ONE : u_sum;

    // ---- Anomaly suppression ----
    wire ias_flag = (u_clamped > U_ANOMALY);

    // ---- Register outputs ----
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid_out <= 1'b0;
            w_k       <= 32'd0;
            CV_norm   <= 32'd0;
            S_k       <= 32'd0;
            U_k       <= 32'd0;
            IAS_k     <= 1'b0;
            C_k_out   <= 4'd1;
        end else begin
            valid_out <= valid_in;
            if (valid_in) begin
                w_k     <= w_clamped;
                CV_norm <= cv_clamped;
                S_k     <= w_clamped;     // score = salience
                U_k     <= u_clamped;
                IAS_k   <= ias_flag;
                C_k_out <= C_k;
            end
        end
    end

endmodule
