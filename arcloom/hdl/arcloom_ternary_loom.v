// ============================================================
// ArcLoom Ternary Loom Core — FPGA Hardware
// ============================================================
//
// This IS ArcLoom. Not binary. Not software. Hardware.
//
// Each trit: 2 wires encoding {-1, 0, +1}
//   00 = 0 (null/undecided)
//   01 = +1 (positive)
//   10 = -1 (negative)
//   11 = invalid (never produced)
//
// 6 strands × 3 trits = 18 trits = 36 wires
// Strands: distance[3], direction[3], accel[3],
//          context[3], momentum[3], DECISION[3]
//
// The coupling matrix is hardwired connections between trits.
// Settling happens combinationally — ALL trits evaluate
// their local field in ONE clock cycle. O(1).
//
// Krimelack: shift register storing last N states.
// Recalled by pattern matching against current input.
//
// Target: PYNQ-Z2 (Zynq-7020)
// ============================================================

module arcloom_trit (
    // One ternary digit
    input  wire [1:0] trit_in,    // 00=0, 01=+1, 10=-1
    output wire       is_pos,     // +1
    output wire       is_neg,     // -1
    output wire       is_null     //  0
);
    assign is_pos  = (trit_in == 2'b01);
    assign is_neg  = (trit_in == 2'b10);
    assign is_null = (trit_in == 2'b00);
endmodule


// ============================================================
// Ternary multiply: trit × signed weight → signed result
// ============================================================
module arcloom_trit_mult (
    input  wire [1:0]  trit,         // 00=0, 01=+1, 10=-1
    input  wire [7:0]  weight,       // signed 8-bit weight
    output wire [7:0]  result        // signed 8-bit result
);
    wire [7:0] neg_weight;
    assign neg_weight = (~weight) + 8'd1;  // -weight (2's complement)

    assign result = (trit == 2'b01) ? weight :      // +1 × w = w
                    (trit == 2'b10) ? neg_weight :   // -1 × w = -w
                    8'd0;                             //  0 × w = 0
endmodule


// ============================================================
// Ternary local field: sum of coupled trit contributions
// ============================================================
module arcloom_local_field #(
    parameter N_INPUTS = 9  // number of input trits coupled to this trit
)(
    input  wire [2*N_INPUTS-1:0] coupled_trits,  // packed trit inputs
    input  wire [8*N_INPUTS-1:0] weights,        // packed signed weights
    input  wire [7:0]            external_h,     // external field (from sensor)
    output wire [1:0]            trit_out,       // settled trit value
    output wire [15:0]           field_value     // for debug: raw field
);
    // Compute weighted sum of all coupled trits + external field
    integer i;
    reg signed [15:0] total;

    always @(coupled_trits or weights or external_h) begin
        total = {{8{external_h[7]}}, external_h};  // sign-extend external
        for (i = 0; i < N_INPUTS; i = i + 1) begin
            case (coupled_trits[2*i +: 2])
                2'b01:   total = total + {{8{weights[8*i+7]}}, weights[8*i +: 8]};
                2'b10:   total = total - {{8{weights[8*i+7]}}, weights[8*i +: 8]};
                default: ;  // null contributes nothing
            endcase
        end
    end

    // Dead zone: the ternary threshold
    // If |field| < DEAD_ZONE, trit stays at 0 (null/undecided)
    localparam signed [15:0] DEAD_ZONE = 16'd20;

    assign trit_out = (total > DEAD_ZONE)  ? 2'b01 :   // +1
                      (total < -DEAD_ZONE) ? 2'b10 :    // -1
                      2'b00;                              //  0 (null)

    assign field_value = total;
endmodule


// Krimelack is now in arcloom_krimelack.v (spec-compliant standalone module)


// ============================================================
// BSIL — Binary Story Ingestion Layer
// ============================================================
// Converts binary sensor data (ADC voltage) to ternary trits
// This IS the bridge between binary reality and ternary ArcLoom
//
module arcloom_bsil (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [11:0] adc_value,     // 12-bit ADC reading (0-4095)
    input  wire        adc_valid,     // ADC data valid pulse

    // Ternary output: 3 strands × 3 trits = 9 trits = 18 bits
    output reg [5:0]   distance_strand,  // 3 trits
    output reg [5:0]   direction_strand, // 3 trits
    output reg [5:0]   accel_strand      // 3 trits
);
    // Threshold constants (12-bit ADC scale: 0-4095)
    // Sharp sensor: high value = close, low value = far
    localparam [11:0] DIST_LO_0 = 12'd400;   // ~0.3V
    localparam [11:0] DIST_HI_0 = 12'd1860;  // ~1.5V
    localparam [11:0] DIST_LO_1 = 12'd990;   // ~0.8V
    localparam [11:0] DIST_HI_1 = 12'd2480;  // ~2.0V
    localparam [11:0] DIST_LO_2 = 12'd1860;  // ~1.5V
    localparam [11:0] DIST_HI_2 = 12'd3100;  // ~2.5V

    localparam [11:0] DELTA_THRESH_0 = 12'd62;   // ~0.05V
    localparam [11:0] DELTA_THRESH_1 = 12'd186;  // ~0.15V
    localparam [11:0] DELTA_THRESH_2 = 12'd372;  // ~0.30V

    localparam [11:0] ACCEL_THRESH_0 = 12'd37;   // ~0.03V
    localparam [11:0] ACCEL_THRESH_1 = 12'd99;   // ~0.08V
    localparam [11:0] ACCEL_THRESH_2 = 12'd186;  // ~0.15V

    // History for delta and acceleration
    reg [11:0] prev_value;
    reg [11:0] prev_prev_value;
    reg        has_prev;
    reg        has_prev2;

    // Signed delta computation
    wire signed [12:0] delta;
    wire signed [12:0] prev_delta;
    wire signed [12:0] accel;

    assign delta = {1'b0, adc_value} - {1'b0, prev_value};
    assign prev_delta = {1'b0, prev_value} - {1'b0, prev_prev_value};
    assign accel = delta - prev_delta;

    // Ternary encode function (inline)
    // Returns 2'b01 (+1) if val > hi, 2'b10 (-1) if val < lo, 2'b00 (0) otherwise
    function [1:0] encode_trit;
        input [11:0] val;
        input [11:0] lo;
        input [11:0] hi;
        begin
            if (val > hi)
                encode_trit = 2'b01;
            else if (val < lo)
                encode_trit = 2'b10;
            else
                encode_trit = 2'b00;
        end
    endfunction

    function [1:0] encode_delta_trit;
        input signed [12:0] d;
        input [11:0] thresh;
        begin
            if (d > $signed({1'b0, thresh}))
                encode_delta_trit = 2'b01;
            else if (d < -$signed({1'b0, thresh}))
                encode_delta_trit = 2'b10;
            else
                encode_delta_trit = 2'b00;
        end
    endfunction

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            distance_strand  <= 6'b0;
            direction_strand <= 6'b0;
            accel_strand     <= 6'b0;
            prev_value       <= 12'd0;
            prev_prev_value  <= 12'd0;
            has_prev         <= 1'b0;
            has_prev2        <= 1'b0;
        end else if (adc_valid) begin
            // Distance strand
            distance_strand[1:0] <= encode_trit(adc_value, DIST_LO_0, DIST_HI_0);
            distance_strand[3:2] <= encode_trit(adc_value, DIST_LO_1, DIST_HI_1);
            distance_strand[5:4] <= encode_trit(adc_value, DIST_LO_2, DIST_HI_2);

            // Direction strand
            if (has_prev) begin
                direction_strand[1:0] <= encode_delta_trit(delta, DELTA_THRESH_0);
                direction_strand[3:2] <= encode_delta_trit(delta, DELTA_THRESH_1);
                direction_strand[5:4] <= encode_delta_trit(delta, DELTA_THRESH_2);
            end else begin
                direction_strand <= 6'b0;
            end

            // Acceleration strand
            if (has_prev2) begin
                accel_strand[1:0] <= encode_delta_trit(accel, ACCEL_THRESH_0);
                accel_strand[3:2] <= encode_delta_trit(accel, ACCEL_THRESH_1);
                accel_strand[5:4] <= encode_delta_trit(accel, ACCEL_THRESH_2);
            end else begin
                accel_strand <= 6'b0;
            end

            // Update history
            prev_prev_value <= prev_value;
            prev_value      <= adc_value;
            has_prev2       <= has_prev;
            has_prev        <= 1'b1;
        end
    end
endmodule


// ============================================================
// ArcLoom Top Module — 8-Strand SPPU + UF Pipeline + Krimelack
// ============================================================
//
// 8 strands x 3 trits = 24 trits = 48 bits.
//
// Architecture:
//   clk/rst_n drive ONLY: BSIL, Krimelack, UF Pipeline
//   The SPPU (loom fabric) is PURELY COMBINATIONAL — no clock.
//
//   BSIL (clocked) → 3 input strands (distance/direction/accel)
//   Camera BSIL (ARM) → 2 input strands (edge/motion) via AXI
//   SPPU (combinational) → 48-bit loom_state
//   Krimelack (clocked) → structural memory with commit gating
//   UF Pipeline (clocked) → DSF → feedback bias into SPPU
//   L6 (combinational) → structural lock detection
// ============================================================
module arcloom_top (
    input  wire        clk,
    input  wire        rst_n,

    // Sensor input (from XADC or external ADC)
    input  wire [11:0] sensor_adc,
    input  wire        sensor_valid,

    // Camera strands (from ARM via AXI — null when camera not connected)
    input  wire [5:0]  cam_edge_strand,
    input  wire [5:0]  cam_motion_strand,

    // Decision output
    output wire [1:0]  decision_steer,
    output wire [1:0]  decision_speed,
    output wire [1:0]  decision_conf,

    // Status outputs
    output wire        structural_lock,
    output wire        dsf_safe_mode,
    output wire        dsf_valid,
    output wire [1:0]  dsf_D,
    output wire        dsf_R_rev,

    // Monitor outputs (via AXI)
    output wire [47:0] loom_state,
    output wire [4:0]  n_effective,
    output wire [7:0]  omega,

    // Krimelack status
    output wire [5:0]  krimelack_count,
    output wire [7:0]  krimelack_score,
    output wire        krimelack_recall_valid,
    output wire        krimelack_commit_accepted,
    output wire        krimelack_commit_rejected
);

    // Internal UF pipeline signals
    wire [31:0] dsf_M, dsf_U_star, dsf_P, dsf_B;
    wire [3:0]  dsf_C;
    wire        l0_boundary_w;

    // ================================================================
    // BSIL: Binary Sensor → Ternary Strands (CLOCKED)
    // ================================================================
    wire [5:0] dist_strand, dir_strand, accl_strand;

    arcloom_bsil bsil_inst (
        .clk(clk), .rst_n(rst_n),
        .adc_value(sensor_adc), .adc_valid(sensor_valid),
        .distance_strand(dist_strand),
        .direction_strand(dir_strand),
        .accel_strand(accl_strand)
    );

    // ================================================================
    // DSF Feedback Bias
    // ================================================================
    reg [7:0] dsf_bias_dcsn, dsf_bias_mmtm;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dsf_bias_dcsn <= 8'd0;
            dsf_bias_mmtm <= 8'd0;
        end else if (dsf_valid && !dsf_safe_mode) begin
            case (dsf_D)
                2'b01:   dsf_bias_dcsn <= dsf_B[23:16];
                2'b10:   dsf_bias_dcsn <= ~dsf_B[23:16] + 8'd1;
                default: dsf_bias_dcsn <= 8'd0;
            endcase
            dsf_bias_mmtm <= dsf_M[31] ? (~dsf_M[23:16] + 8'd1) : dsf_M[23:16];
        end else if (dsf_valid && dsf_safe_mode) begin
            dsf_bias_dcsn <= 8'd0;
            dsf_bias_mmtm <= 8'd0;
        end
    end

    // ================================================================
    // SPPU: 8-Strand Loom Fabric (COMBINATIONAL — NO CLOCK)
    // ================================================================
    arcloom_sppu sppu_inst (
        .in_distance(dist_strand),
        .in_direction(dir_strand),
        .in_accel(accl_strand),
        .in_cam_edge(cam_edge_strand),
        .in_cam_motion(cam_motion_strand),
        .ext_h_ctx(8'd0),
        .ext_h_mmtm(dsf_bias_mmtm),
        .ext_h_dcsn(dsf_bias_dcsn),
        .loom_state(loom_state),
        .decision_steer(decision_steer),
        .decision_speed(decision_speed),
        .decision_conf(decision_conf),
        .field_ctx_0(), .field_ctx_1(), .field_ctx_2(),
        .field_mmtm_0(), .field_mmtm_1(), .field_mmtm_2(),
        .field_dcsn_0(), .field_dcsn_1(), .field_dcsn_2()
    );

    // ================================================================
    // Krimelack: Structural Memory (CLOCKED — spec-compliant)
    // ================================================================
    wire [47:0] recalled_motif;

    // DSF resonance for commit eligibility
    // Use a simple proxy: resonance high when uncertainty low
    wire [31:0] resonance_proxy = (dsf_U_star <= 32'h00008000) ?
                                   32'h0000C000 : 32'h00004000;

    arcloom_krimelack #(.TRIT_WIDTH(48), .DEPTH(32)) krimelack_inst (
        .clk(clk), .rst_n(rst_n),
        .commit_request(dsf_valid),
        .state_in(loom_state),
        .u_star(dsf_U_star),
        .resonance(resonance_proxy),
        .safe_mode(dsf_safe_mode),
        .query(loom_state),
        .best_match(recalled_motif),
        .match_score(krimelack_score),
        .recall_valid(krimelack_recall_valid),
        .motif_count(krimelack_count),
        .commit_accepted(krimelack_commit_accepted),
        .commit_rejected(krimelack_commit_rejected)
    );

    // ================================================================
    // UF Pipeline: L0 → L1 → L2 → L3 → L4 (CLOCKED)
    // ================================================================
    wire [31:0] f_norm_approx = {4'd0, sensor_adc, 16'd0};

    arcloom_uf_pipeline uf_pipeline_inst (
        .clk(clk), .rst_n(rst_n),
        .valid_in(sensor_valid),
        .F_norm_in(f_norm_approx),
        .dsf_valid(dsf_valid),
        .dsf_D(dsf_D),
        .dsf_M(dsf_M),
        .dsf_R_rev(dsf_R_rev),
        .dsf_U_star(dsf_U_star),
        .dsf_C(dsf_C),
        .dsf_P(dsf_P),
        .dsf_B(dsf_B),
        .dsf_safe_mode(dsf_safe_mode),
        .l0_valid(), .l0_dF(), .l0_sigma(), .l0_kappa(),
        .l0_N(), .l0_boundary(l0_boundary_w), .l0_D_t()
    );

    // ================================================================
    // L6: Topological Constraint Layer (COMBINATIONAL)
    // 24 trits, knee at 24/e ≈ 8.83 → KNEE=9
    // SL-1 fires when 16+ of 24 trits are non-null
    // ================================================================
    arcloom_l6_tcl #(.N_TRITS(24), .KNEE(9)) l6_inst (
        .loom_state(loom_state),
        .disruption_active(l0_boundary_w),
        .recovery_pending(dsf_safe_mode),
        .structural_lock(structural_lock),
        .n_effective(n_effective),
        .n_collapsed(),
        .omega(omega)
    );

endmodule
