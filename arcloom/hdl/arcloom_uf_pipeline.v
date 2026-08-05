// ============================================================
// ArcLoom UF Pipeline — Complete L0 → L4 Chain
// ============================================================
//
// Instantiates and connects all five UF kernel layers:
//   L0: Structural normalization + boundary detection (per-sample)
//   L1: Gate formation + mosaic projection (per-sample → per-gate)
//   L2: Interpretive metrics (per-gate)
//   L3: Resonance + contextual gating (per-gate)
//   L4: DSF generation + SafeMode (per-gate)
//
// Input:  log-normalized field value F_norm (16.16 fixed-point)
// Output: Complete DSF tuple + SafeMode flag
//
// The L0 module operates per-sample (every valid_in pulse).
// L1 accumulates samples into gates and emits per-gate.
// L2-L4 each add one pipeline stage per gate.
// Total latency: 4 clock cycles per gate (after L1 emits).
//
// Target: PYNQ-Z2 (Zynq-7020)
// ============================================================

module arcloom_uf_pipeline (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] F_norm_in,     // log-normalized field value (16.16)

    // DSF output (per-gate)
    output wire        dsf_valid,
    output wire [1:0]  dsf_D,         // direction trit
    output wire signed [31:0] dsf_M,  // momentum
    output wire        dsf_R_rev,     // reversal flag
    output wire [31:0] dsf_U_star,    // adjusted uncertainty
    output wire [3:0]  dsf_C,         // mosaic divergence
    output wire [31:0] dsf_P,         // pressure
    output wire [31:0] dsf_B,         // breathing
    output wire        dsf_safe_mode, // SafeMode active

    // L0 debug outputs (per-sample)
    output wire        l0_valid,
    output wire [31:0] l0_dF,
    output wire [31:0] l0_sigma,
    output wire [31:0] l0_kappa,
    output wire        l0_N,
    output wire        l0_boundary,
    output wire [31:0] l0_D_t
);

    // ================================================================
    // L0: Structural Normalization + Boundary Detection
    // ================================================================
    wire        l0_valid_w;
    wire [31:0] l0_dF_w;        // signed
    wire [31:0] l0_sigma_w;
    wire [31:0] l0_kappa_w;
    wire        l0_N_w;
    wire [31:0] l0_D_t_w;
    wire        l0_boundary_w;

    arcloom_l0_sev l0_inst (
        .clk(clk), .rst_n(rst_n),
        .valid_in(valid_in),
        .F_norm_in(F_norm_in),
        .valid_out(l0_valid_w),
        .F_norm_out(),
        .dF_out(l0_dF_w),
        .sigma_out(l0_sigma_w),
        .kappa_out(l0_kappa_w),
        .N_out(l0_N_w),
        .D_t_out(l0_D_t_w),
        .gate_boundary(l0_boundary_w),
        .gate_count()
    );

    // Debug taps
    assign l0_valid    = l0_valid_w;
    assign l0_dF       = l0_dF_w;
    assign l0_sigma    = l0_sigma_w;
    assign l0_kappa    = l0_kappa_w;
    assign l0_N        = l0_N_w;
    assign l0_boundary = l0_boundary_w;
    assign l0_D_t      = l0_D_t_w;

    // |dF| for L1 (absolute value of signed dF)
    wire [31:0] abs_dF;
    assign abs_dF = l0_dF_w[31] ? (~l0_dF_w + 32'd1) : l0_dF_w;

    // ================================================================
    // L1: Gate Formation + Mosaic Projection
    // ================================================================
    wire        l1_valid;
    wire [31:0] l1_T_k, l1_V_k, l1_R_k;
    wire [3:0]  l1_C_k;
    wire [15:0] l1_N_sum, l1_T_count;
    wire [31:0] l1_dF_max, l1_dF_min;

    arcloom_l1_gate l1_inst (
        .clk(clk), .rst_n(rst_n),
        .valid_in(l0_valid_w),
        .abs_dF(abs_dF),
        .sigma(l0_sigma_w),
        .kappa(l0_kappa_w),
        .boundary_in(l0_boundary_w),
        .N_in(l0_N_w),
        .valid_out(l1_valid),
        .T_k(l1_T_k),
        .V_k(l1_V_k),
        .R_k(l1_R_k),
        .C_k(l1_C_k),
        .N_sum_out(l1_N_sum),
        .T_count_out(l1_T_count),
        .dF_max_out(l1_dF_max),
        .dF_min_out(l1_dF_min)
    );

    // ================================================================
    // L2: Interpretive Metrics
    // ================================================================
    wire        l2_valid;
    wire [31:0] l2_w_k, l2_CV_norm, l2_S_k, l2_U_k;
    wire        l2_IAS_k;
    wire [3:0]  l2_C_k;

    arcloom_l2_metrics l2_inst (
        .clk(clk), .rst_n(rst_n),
        .valid_in(l1_valid),
        .V_k(l1_V_k),
        .C_k(l1_C_k),
        .N_sum(l1_N_sum),
        .T_count(l1_T_count),
        .dF_max(l1_dF_max),
        .dF_min(l1_dF_min),
        .valid_out(l2_valid),
        .w_k(l2_w_k),
        .CV_norm(l2_CV_norm),
        .S_k(l2_S_k),
        .U_k(l2_U_k),
        .IAS_k(l2_IAS_k),
        .C_k_out(l2_C_k)
    );

    // ================================================================
    // L3: Resonance + Contextual Gating
    // ================================================================
    wire        l3_valid;
    wire [31:0] l3_R_scalar, l3_URF_k;
    wire        l3_g_k, l3_Hyst_k;
    wire [31:0] l3_U_k;
    wire        l3_IAS_k;
    wire [3:0]  l3_C_k;

    arcloom_l3_resonance l3_inst (
        .clk(clk), .rst_n(rst_n),
        .valid_in(l2_valid),
        .w_k(l2_w_k),
        .CV_norm(l2_CV_norm),
        .S_k(l2_S_k),
        .U_k(l2_U_k),
        .IAS_k(l2_IAS_k),
        .C_k(l2_C_k),
        .valid_out(l3_valid),
        .R_scalar(l3_R_scalar),
        .URF_k(l3_URF_k),
        .g_k(l3_g_k),
        .Hyst_k(l3_Hyst_k),
        .U_k_out(l3_U_k),
        .IAS_k_out(l3_IAS_k),
        .C_k_out(l3_C_k)
    );

    // ================================================================
    // L4: DSF Generation + SafeMode
    // ================================================================
    arcloom_l4_dsf l4_inst (
        .clk(clk), .rst_n(rst_n),
        .valid_in(l3_valid),
        .R_scalar(l3_R_scalar),
        .Hyst_k(l3_Hyst_k),
        .U_k(l3_U_k),
        .IAS_k(l3_IAS_k),
        .C_k(l3_C_k),
        .valid_out(dsf_valid),
        .D_k(dsf_D),
        .M_k(dsf_M),
        .R_rev_k(dsf_R_rev),
        .U_star_k(dsf_U_star),
        .C_k_out(dsf_C),
        .P_k(dsf_P),
        .B_k(dsf_B),
        .safe_mode(dsf_safe_mode)
    );

endmodule
