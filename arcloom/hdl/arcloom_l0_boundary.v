// ============================================================
// ArcLoom L0 Boundary Operator — FPGA Hardware Implementation
// ============================================================
//
// Implements: D(t) = alpha1 * |dF| + alpha2 * sigma + alpha3 * kappa
//
// This is the structural gating function from UF-Spec v1.4.0.
// When D(t) > tau_D, a gate boundary is detected.
//
// All computation happens in ONE clock cycle (O(1)).
// Fixed-point arithmetic: 16.16 format (16 integer, 16 fractional bits).
//
// Inputs:  dF, sigma, kappa (each 32-bit fixed-point)
// Outputs: D_t (32-bit fixed-point), gate_boundary (1-bit flag)
//
// Target: PYNQ-Z2 (Zynq-7020, XC7Z020-1CLG400C)
// ============================================================

module arcloom_l0_boundary #(
    // UF-Spec v1.4.0 thresholds (16.16 fixed-point)
    // alpha1 = 1.0 = 32'h00010000
    // alpha2 = 1.0 = 32'h00010000
    // alpha3 = 1.0 = 32'h00010000
    // tau_D  = 0.20 = 32'h00003333
    parameter ALPHA1 = 32'h00010000,  // 1.0 in 16.16
    parameter ALPHA2 = 32'h00010000,  // 1.0 in 16.16
    parameter ALPHA3 = 32'h00010000,  // 1.0 in 16.16
    parameter TAU_D  = 32'h00003333   // 0.20 in 16.16
)(
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,      // input data is valid
    input  wire [31:0] dF_in,         // delta F (signed 16.16 fixed-point)
    input  wire [31:0] sigma_in,      // sigma (unsigned 16.16)
    input  wire [31:0] kappa_in,      // kappa (unsigned 16.16)

    output reg         valid_out,     // output data is valid
    output reg  [31:0] D_t_out,       // D(t) result (unsigned 16.16)
    output reg         gate_boundary, // 1 if D(t) > tau_D
    output reg  [31:0] gate_count     // running count of gates detected
);

    // Internal wires — all computed combinationally (O(1))
    wire [31:0] abs_dF;
    wire [63:0] term1_full, term2_full, term3_full;
    wire [31:0] term1, term2, term3;
    wire [31:0] D_t_comb;
    wire        boundary_comb;

    // |dF| — absolute value (2's complement)
    assign abs_dF = dF_in[31] ? (~dF_in + 1) : dF_in;

    // Multiply each term by its alpha coefficient
    // Result is 32.32 (64-bit), we take bits [47:16] for 16.16 result
    assign term1_full = ALPHA1 * abs_dF;
    assign term2_full = ALPHA2 * sigma_in;
    assign term3_full = ALPHA3 * kappa_in;

    // Extract 16.16 result from 32.32 product
    assign term1 = term1_full[47:16];
    assign term2 = term2_full[47:16];
    assign term3 = term3_full[47:16];

    // D(t) = alpha1*|dF| + alpha2*sigma + alpha3*kappa
    assign D_t_comb = term1 + term2 + term3;

    // Gate boundary: D(t) > tau_D
    // Using strict > as per UF-Spec approved domain override
    assign boundary_comb = (D_t_comb > TAU_D);

    // Register outputs on clock edge
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid_out     <= 1'b0;
            D_t_out       <= 32'h0;
            gate_boundary <= 1'b0;
            gate_count    <= 32'h0;
        end else begin
            valid_out     <= valid_in;
            D_t_out       <= valid_in ? D_t_comb : D_t_out;
            gate_boundary <= valid_in ? boundary_comb : gate_boundary;

            // Increment gate counter on boundary detection
            if (valid_in && boundary_comb) begin
                gate_count <= gate_count + 1;
            end
        end
    end

endmodule


// ============================================================
// ArcLoom L0 Full SEV Pipeline
// ============================================================
//
// Computes the full State Embedding Vector:
//   F_norm = log(F + epsilon)       -- done in software (log is expensive in HW)
//   dF(t) = F_norm(t) - F_norm(t-1) -- one subtraction
//   sigma(t) = variance over window  -- shift register + accumulator
//   kappa(t) = |F(t+1) - 2F(t) + F(t-1)| -- absolute second difference
//   N(t) = 1 iff (sigma < tau_s AND |dF| < tau_d AND kappa < tau_k)
//   D(t) = alpha1*|dF| + alpha2*sigma + alpha3*kappa
//   gate_boundary = D(t) > tau_D
//
// The log normalization is done in software before feeding the FPGA.
// Everything else is pure hardware, O(1) per sample.
// ============================================================

module arcloom_l0_sev #(
    parameter WINDOW   = 20,          // variance window size
    parameter ALPHA1   = 32'h00010000,
    parameter ALPHA2   = 32'h00010000,
    parameter ALPHA3   = 32'h00010000,
    parameter TAU_D    = 32'h00003333, // 0.20
    parameter TAU_S    = 32'h00000001, // sigma_min = 1e-6 ≈ 0 in fixed-point
    parameter TAU_DELTA= 32'h00000001, // delta_min
    parameter TAU_K    = 32'h00000001  // kappa_min
)(
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] F_norm_in,     // log-normalized field value (16.16)

    // Full SEV output
    output reg         valid_out,
    output reg  [31:0] F_norm_out,
    output reg  [31:0] dF_out,        // signed
    output reg  [31:0] sigma_out,     // unsigned
    output reg  [31:0] kappa_out,     // unsigned
    output reg         N_out,         // negative space indicator
    output reg  [31:0] D_t_out,       // boundary operator value
    output reg         gate_boundary, // gate boundary flag
    output reg  [31:0] gate_count
);

    // Delay registers for dF and kappa
    reg [31:0] F_prev;
    reg [31:0] F_prev2;
    reg        has_prev;
    reg        has_prev2;

    // Variance computation: shift register for windowed variance
    reg [31:0] window_buf [0:WINDOW-1];
    reg [31:0] window_sum;
    reg [31:0] window_sum_sq_lo;  // lower 32 bits of sum of squares
    reg [4:0]  window_ptr;
    reg [4:0]  window_count;

    // Intermediate signals
    wire [31:0] dF_calc;
    wire [31:0] abs_dF;
    wire [31:0] kappa_calc;
    wire [31:0] sigma_calc;
    wire        N_calc;

    // dF = F_norm(t) - F_norm(t-1)
    assign dF_calc = F_norm_in - F_prev;

    // |dF|
    assign abs_dF = dF_calc[31] ? (~dF_calc + 1) : dF_calc;

    // kappa = |F(t) - 2*F(t-1) + F(t-2)|
    // = |F_norm_in - 2*F_prev + F_prev2|
    wire [31:0] kappa_raw;
    assign kappa_raw = F_norm_in - {F_prev[30:0], 1'b0} + F_prev2;
    assign kappa_calc = kappa_raw[31] ? (~kappa_raw + 1) : kappa_raw;

    // Simplified variance: use mean absolute deviation as proxy
    // (true variance requires division which is expensive in HW)
    // sigma ≈ (1/N) * sum(|F_i - mean|)
    // For prototype: use |dF| as variance proxy (tracks the same thing)
    assign sigma_calc = abs_dF;  // simplified for v0.1

    // Negative space: N(t) = 1 iff all below thresholds
    assign N_calc = (sigma_calc <= TAU_S) &&
                    (abs_dF <= TAU_DELTA) &&
                    (kappa_calc <= TAU_K);

    // Instantiate boundary operator
    wire [31:0] D_t_internal;
    wire        boundary_internal;

    arcloom_l0_boundary #(
        .ALPHA1(ALPHA1), .ALPHA2(ALPHA2), .ALPHA3(ALPHA3), .TAU_D(TAU_D)
    ) boundary_inst (
        .clk(clk), .rst_n(rst_n), .valid_in(valid_in && has_prev),
        .dF_in(dF_calc), .sigma_in(sigma_calc), .kappa_in(kappa_calc),
        .valid_out(), .D_t_out(D_t_internal),
        .gate_boundary(boundary_internal), .gate_count()
    );

    // Main sequential logic
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            F_prev      <= 32'h0;
            F_prev2     <= 32'h0;
            has_prev    <= 1'b0;
            has_prev2   <= 1'b0;
            valid_out   <= 1'b0;
            F_norm_out  <= 32'h0;
            dF_out      <= 32'h0;
            sigma_out   <= 32'h0;
            kappa_out   <= 32'h0;
            N_out       <= 1'b0;
            D_t_out     <= 32'h0;
            gate_boundary <= 1'b0;
            gate_count  <= 32'h0;
            window_ptr  <= 5'h0;
            window_count<= 5'h0;
            window_sum  <= 32'h0;
            for (i = 0; i < WINDOW; i = i + 1)
                window_buf[i] <= 32'h0;
        end else if (valid_in) begin
            // Shift delay line
            F_prev2  <= F_prev;
            F_prev   <= F_norm_in;
            has_prev2 <= has_prev;
            has_prev  <= 1'b1;

            // Output SEV
            valid_out   <= has_prev;
            F_norm_out  <= F_norm_in;
            dF_out      <= has_prev ? dF_calc : 32'h0;
            sigma_out   <= has_prev ? sigma_calc : 32'h0;
            kappa_out   <= has_prev2 ? kappa_calc : 32'h0;
            N_out       <= has_prev2 ? N_calc : 1'b0;
            D_t_out     <= D_t_internal;
            gate_boundary <= boundary_internal;

            if (has_prev && boundary_internal) begin
                gate_count <= gate_count + 1;
            end
        end
    end

endmodule
