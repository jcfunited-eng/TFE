// ============================================================
// ArcLoom L4 — Decision Surface Vector (DSF) Generation
// ============================================================
//
// UF-Spec L4: Generates final bounded decision vector.
//
// DSF_k = (D_k, M_k, R_rev_k, U_star_k, C_k, P_k, B_k)
//
//   D_k     = direction {-1, 0, +1} (ternary)
//   M_k     = momentum: R(k) - 2R(k-1) + R(k-2)
//   R_rev_k = reversal flag {0,1}
//   U_star_k= adjusted uncertainty in [0,1]
//   C_k     = mosaic divergence (pass-through)
//   P_k     = pressure |D_k - D_{k-1}| in {0,1,2}
//   B_k     = breathing bandwidth in [B_min, B_max]
//
// SafeMode: S(UF) < S_min triggers freeze.
//   S(UF) = lambda_b*(1 - Var(B)) + lambda_u*(1 - U_bar)
//   Var(B) over K_s=8 gate window.
//   Recovery requires all conditions met for DWELL gates.
//
// All arithmetic: 16.16 fixed-point (signed where noted).
// Target: PYNQ-Z2 (Zynq-7020)
// ============================================================

module arcloom_l4_dsf #(
    // Direction threshold
    parameter EPS_D      = 32'h00000CCC,  // 0.05 in 16.16

    // Uncertainty adjustment penalties
    parameter ETA_H      = 32'h00002666,  // 0.15
    parameter ETA_IAS    = 32'h00003333,  // 0.20

    // Breathing coefficients
    parameter XI         = 32'h00001475,  // 0.08 (growth)
    parameter CHI        = 32'h00003333,  // 0.20 (contraction)
    parameter B_MIN      = 32'h0000199A,  // 0.1
    parameter B_MAX      = 32'h00010000,  // 1.0
    parameter B_INIT     = 32'h00008000,  // 0.5 initial

    // SafeMode
    parameter K_S        = 8,             // stability window (power of 2)
    parameter K_S_SHIFT  = 3,             // log2(K_S)
    parameter S_MIN      = 32'h00006666,  // 0.4 — SafeMode threshold
    parameter LAMBDA_B   = 32'h00008000,  // 0.5
    parameter LAMBDA_U   = 32'h00008000,  // 0.5
    parameter DWELL      = 4             // recovery dwell gates
)(
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] R_scalar,      // R(k) from L3
    input  wire        Hyst_k,        // hysteresis flag from L3
    input  wire [31:0] U_k,           // uncertainty from L3
    input  wire        IAS_k,         // anomaly flag from L3
    input  wire [3:0]  C_k,           // mosaic divergence from L3

    output reg         valid_out,
    // DSF tuple
    output reg  [1:0]  D_k,           // direction trit: 00=0, 01=+1, 10=-1
    output reg signed [31:0] M_k,     // momentum (signed 16.16)
    output reg         R_rev_k,       // reversal flag
    output reg  [31:0] U_star_k,      // adjusted uncertainty [0,1]
    output reg  [3:0]  C_k_out,       // pass-through
    output reg  [31:0] P_k,           // pressure [0, 2.0] in 16.16
    output reg  [31:0] B_k,           // breathing [B_min, B_max]
    output reg         safe_mode      // SafeMode active flag
);

    localparam [31:0] ONE = 32'h00010000;  // 1.0
    localparam [31:0] TWO = 32'h00020000;  // 2.0

    // ---- History registers ----
    reg [31:0] R_prev;       // R(k-1)
    reg [31:0] R_prev2;      // R(k-2)
    reg [1:0]  D_prev;       // D(k-1)
    reg [31:0] B_prev;       // B(k-1)
    reg        has_prev;
    reg        has_prev2;

    // ---- Delta R (signed) ----
    wire signed [31:0] delta_R = $signed({1'b0, R_scalar[30:0]}) -
                                  $signed({1'b0, R_prev[30:0]});

    // ---- Direction (ternary) ----
    wire [1:0] d_val;
    assign d_val = (delta_R > $signed(EPS_D))   ? 2'b01 :  // +1
                   (delta_R < -$signed(EPS_D))   ? 2'b10 :  // -1
                   2'b00;                                     //  0

    // ---- Momentum: R(k) - 2*R(k-1) + R(k-2) ----
    wire signed [31:0] m_val;
    assign m_val = $signed({1'b0, R_scalar[30:0]}) -
                   $signed({R_prev[30:0], 1'b0}) +
                   $signed({1'b0, R_prev2[30:0]});

    // ---- Reversal: D_k * D_{k-1} < 0 ----
    // Reversal if one is +1 and other is -1
    wire rev_val = (d_val == 2'b01 && D_prev == 2'b10) ||
                   (d_val == 2'b10 && D_prev == 2'b01);

    // ---- Adjusted uncertainty: U* = clamp(U + eta_H*Hyst + eta_IAS*IAS, 0, 1) ----
    wire [31:0] u_adj = U_k +
                        (Hyst_k ? ETA_H : 32'd0) +
                        (IAS_k  ? ETA_IAS : 32'd0);
    wire [31:0] u_star_val = (u_adj > ONE) ? ONE : u_adj;

    // ---- Pressure: |D_k - D_{k-1}| ----
    // D encoded as trit. Convert to signed for subtraction.
    wire signed [2:0] d_signed = (d_val == 2'b01) ? 3'sd1 :
                                  (d_val == 2'b10) ? -3'sd1 : 3'sd0;
    wire signed [2:0] d_prev_signed = (D_prev == 2'b01) ? 3'sd1 :
                                       (D_prev == 2'b10) ? -3'sd1 : 3'sd0;
    wire signed [2:0] p_diff = d_signed - d_prev_signed;
    wire [31:0] p_val = (p_diff[2]) ?
                        ({16'd0, -p_diff, 13'd0}) :   // |negative| * 2^16... wait
                        ({16'd0, p_diff, 13'd0});

    // Simpler pressure: just enumerate
    // |diff| can be 0, 1, or 2
    wire [31:0] p_val_clean;
    wire [2:0] p_abs = (p_diff < 0) ? (-p_diff) : p_diff;
    assign p_val_clean = (p_abs == 3'd0) ? 32'd0 :
                         (p_abs == 3'd1) ? ONE :
                         TWO;

    // ---- Breathing: B_k = clamp(B_{k-1} + xi*(1-U*)*dR - chi*U*, B_min, B_max) ----
    wire [31:0] one_minus_ustar = (u_star_val <= ONE) ? (ONE - u_star_val) : 32'd0;

    // xi * (1 - U*)
    wire [63:0] xi_1mu_full = XI * one_minus_ustar;
    wire [31:0] xi_1mu = xi_1mu_full[47:16];

    // xi*(1-U*) * |dR| — magnitude, then apply sign
    wire [31:0] abs_delta_R = delta_R[31] ? (-delta_R) : delta_R;
    wire [63:0] growth_full = xi_1mu * abs_delta_R;
    wire [31:0] growth_mag  = growth_full[47:16];

    // chi * U*
    wire [63:0] decay_full = CHI * u_star_val;
    wire [31:0] decay = decay_full[47:16];

    // B_next = B_prev + growth (signed by dR) - decay
    // Compute as signed 33-bit to handle underflow
    wire signed [32:0] b_next_wide;
    assign b_next_wide = {1'b0, B_prev} +
                         (delta_R[31] ? -{1'b0, growth_mag} : {1'b0, growth_mag}) -
                         {1'b0, decay};

    wire [31:0] b_clamped;
    assign b_clamped = (b_next_wide < $signed({1'b0, B_MIN})) ? B_MIN :
                       (b_next_wide > $signed({1'b0, B_MAX})) ? B_MAX :
                       b_next_wide[31:0];

    // ============================================================
    // SafeMode: S(UF) = lambda_b*(1-Var(B)) + lambda_u*(1-U_bar)
    // ============================================================

    // Shift registers for B and U* over K_s window
    reg [31:0] b_buf   [0:K_S-1];
    reg [31:0] u_buf   [0:K_S-1];
    reg [31:0] sum_B;
    reg [31:0] sum_B_sq;
    reg [31:0] sum_U;
    reg [2:0]  win_ptr;
    reg [3:0]  win_count;

    // Variance(B) = E[B^2] - E[B]^2
    // mean_B = sum_B >> K_S_SHIFT
    // mean_B_sq = sum_B_sq >> K_S_SHIFT
    // var_B = mean_B_sq - mean_B^2
    wire [31:0] mean_B    = sum_B >> K_S_SHIFT;
    wire [31:0] mean_B_sq = sum_B_sq >> K_S_SHIFT;
    wire [63:0] mean_B_squared_full = mean_B * mean_B;
    wire [31:0] mean_B_squared = mean_B_squared_full[47:16];
    wire [31:0] var_B = (mean_B_sq >= mean_B_squared) ?
                        (mean_B_sq - mean_B_squared) : 32'd0;

    // U_bar = sum_U >> K_S_SHIFT
    wire [31:0] u_bar = sum_U >> K_S_SHIFT;

    // S(UF) = lambda_b*(1-Var(B)) + lambda_u*(1-U_bar)
    wire [31:0] one_minus_var = (var_B <= ONE) ? (ONE - var_B) : 32'd0;
    wire [31:0] one_minus_ub  = (u_bar <= ONE) ? (ONE - u_bar) : 32'd0;

    wire [63:0] s_term1_full = LAMBDA_B * one_minus_var;
    wire [63:0] s_term2_full = LAMBDA_U * one_minus_ub;
    wire [31:0] s_uf = s_term1_full[47:16] + s_term2_full[47:16];

    // SafeMode trigger
    wire safe_trigger = (win_count >= K_S) && (s_uf < S_MIN);

    // SafeMode recovery conditions
    wire recovery_ok = (s_uf >= S_MIN) &&
                       (C_k <= 4'd3) &&      // C_k <= C_settle
                       (U_k <= 32'h0000D99A) && // U_k <= U_max (0.85)
                       (b_clamped >= B_MIN) &&
                       (b_clamped <= B_MAX);

    reg        in_safe_mode;
    reg [3:0]  recovery_count;

    // ---- SafeMode DSF (neutralized) ----
    wire [1:0]  safe_D     = 2'b00;        // 0
    wire signed [31:0] safe_M = 32'sd0;    // 0
    wire        safe_R_rev = 1'b0;
    wire [31:0] safe_U_star = ONE;         // 1.0
    wire [31:0] safe_P     = 32'd0;        // 0

    // ---- B^2 for current B value ----
    wire [63:0] b_sq_full = b_clamped * b_clamped;
    wire [31:0] b_sq      = b_sq_full[47:16];

    // ---- Oldest values from window (for running sum update) ----
    wire [31:0] oldest_B = b_buf[win_ptr];
    wire [63:0] oldest_B_sq_full = oldest_B * oldest_B;
    wire [31:0] oldest_B_sq = oldest_B_sq_full[47:16];
    wire [31:0] oldest_U = u_buf[win_ptr];

    // ---- Main sequential logic ----
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid_out      <= 1'b0;
            D_k            <= 2'b00;
            M_k            <= 32'sd0;
            R_rev_k        <= 1'b0;
            U_star_k       <= 32'd0;
            C_k_out        <= 4'd1;
            P_k            <= 32'd0;
            B_k            <= B_INIT;
            safe_mode      <= 1'b0;

            R_prev         <= 32'd0;
            R_prev2        <= 32'd0;
            D_prev         <= 2'b00;
            B_prev         <= B_INIT;
            has_prev       <= 1'b0;
            has_prev2      <= 1'b0;

            in_safe_mode   <= 1'b0;
            recovery_count <= 4'd0;

            sum_B          <= 32'd0;
            sum_B_sq       <= 32'd0;
            sum_U          <= 32'd0;
            win_ptr        <= 3'd0;
            win_count      <= 4'd0;

            for (i = 0; i < K_S; i = i + 1) begin
                b_buf[i] <= B_INIT;
                u_buf[i] <= 32'd0;
            end
        end else begin
            valid_out <= valid_in;

            if (valid_in) begin
                // ---- Update stability window ----
                if (win_count >= K_S) begin
                    // Subtract oldest, add newest
                    sum_B    <= sum_B    - oldest_B    + b_clamped;
                    sum_B_sq <= sum_B_sq - oldest_B_sq + b_sq;
                    sum_U    <= sum_U    - oldest_U    + u_star_val;
                end else begin
                    // Still filling window
                    sum_B    <= sum_B    + b_clamped;
                    sum_B_sq <= sum_B_sq + b_sq;
                    sum_U    <= sum_U    + u_star_val;
                    win_count <= win_count + 4'd1;
                end
                b_buf[win_ptr] <= b_clamped;
                u_buf[win_ptr] <= u_star_val;
                win_ptr <= (win_ptr == K_S-1) ? 3'd0 : win_ptr + 3'd1;

                // ---- SafeMode FSM ----
                if (!in_safe_mode) begin
                    if (safe_trigger) begin
                        in_safe_mode   <= 1'b1;
                        recovery_count <= 4'd0;
                    end
                end else begin
                    if (recovery_ok)
                        recovery_count <= recovery_count + 4'd1;
                    else
                        recovery_count <= 4'd0;

                    if (recovery_count >= DWELL)
                        in_safe_mode <= 1'b0;
                end
                safe_mode <= in_safe_mode | safe_trigger;

                // ---- DSF output ----
                if (in_safe_mode | safe_trigger) begin
                    // SafeMode: neutralized DSF
                    D_k      <= safe_D;
                    M_k      <= safe_M;
                    R_rev_k  <= safe_R_rev;
                    U_star_k <= safe_U_star;
                    C_k_out  <= C_k;
                    P_k      <= safe_P;
                    B_k      <= B_prev;  // hold previous
                end else if (has_prev) begin
                    // Normal operation
                    D_k      <= d_val;
                    M_k      <= has_prev2 ? m_val : 32'sd0;
                    R_rev_k  <= rev_val;
                    U_star_k <= u_star_val;
                    C_k_out  <= C_k;
                    P_k      <= p_val_clean;
                    B_k      <= b_clamped;
                end else begin
                    // First gate: no history yet
                    D_k      <= 2'b00;
                    M_k      <= 32'sd0;
                    R_rev_k  <= 1'b0;
                    U_star_k <= u_star_val;
                    C_k_out  <= C_k;
                    P_k      <= 32'd0;
                    B_k      <= B_INIT;
                end

                // ---- Update history ----
                R_prev2  <= R_prev;
                R_prev   <= R_scalar;
                D_prev   <= d_val;
                B_prev   <= b_clamped;
                has_prev2 <= has_prev;
                has_prev  <= 1'b1;
            end
        end
    end

endmodule
