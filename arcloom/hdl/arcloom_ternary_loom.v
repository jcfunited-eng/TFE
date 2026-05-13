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
    parameter N_INPUTS = 9,
    parameter signed [31:0] DEAD_ZONE = 32'd20
)(
    input  wire [2*N_INPUTS-1:0]  coupled_trits,
    input  wire [16*N_INPUTS-1:0] weights,       // 16-bit signed weights (3^i positional)
    input  wire signed [15:0]     external_h,    // 16-bit signed external field
    input  wire [7:0]             dead_zone_adj, // familiarity raises dead zone
    output wire [1:0]             trit_out,
    output wire signed [31:0]     field_value    // 32-bit for debug
);
    integer i;
    reg signed [31:0] total;

    always @(coupled_trits or weights or external_h) begin
        total = {{16{external_h[15]}}, external_h};  // sign-extend 16→32
        for (i = 0; i < N_INPUTS; i = i + 1) begin
            case (coupled_trits[2*i +: 2])
                2'b01:   total = total + {{16{weights[16*i+15]}}, weights[16*i +: 16]};
                2'b10:   total = total - {{16{weights[16*i+15]}}, weights[16*i +: 16]};
                default: ;
            endcase
        end
    end

    wire signed [31:0] effective_dz = DEAD_ZONE + {24'd0, dead_zone_adj};

    assign trit_out = (total > effective_dz)  ? 2'b01 :
                      (total < -effective_dz) ? 2'b10 :
                      2'b00;

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
    // Threshold constants — DSF-AI derived structural boundaries
    // Source: L1 boundary clustering via tools/derive_sppu_weights.py
    // NOT hand-approximated. Gaps between lo/hi are kernel-identified ambiguity.
    // Trit 0 (coarse): "something ahead?"
    localparam [11:0] DIST_LO_0 = 12'd446;
    localparam [11:0] DIST_HI_0 = 12'd584;
    // Trit 1 (medium): "getting close"
    localparam [11:0] DIST_LO_1 = 12'd619;
    localparam [11:0] DIST_HI_1 = 12'd818;
    // Trit 2 (fine): "close/danger"
    localparam [11:0] DIST_LO_2 = 12'd1006;
    localparam [11:0] DIST_HI_2 = 12'd2406;

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
// ArcLoom Top Module — SPPU + Krimelack + L6
// ============================================================
//
// Architecture:
//   clk/rst_n drive ONLY: BSIL, Krimelack
//   The SPPU (loom fabric) is PURELY COMBINATIONAL — no clock.
//   L6 (topological constraint) is COMBINATIONAL.
//
//   BSIL-BT (clocked) → 3 sensor strands (distance/direction/accel)
//   SPPU (combinational) → loom_state + decisions
//   Krimelack (clocked) → structural memory
//   L6 (combinational) → structural lock / dimensional exhaustion
//
// NO TFE/DSF-AI code. The SPPU is the razor.
// DSF-AI provides coupling weights and thresholds externally.
// ============================================================
module arcloom_top (
    input  wire        clk,
    input  wire        rst_n,

    // 3 sensor inputs (from XADC)
    input  wire [11:0] sensor_adc_front,
    input  wire        sensor_valid_front,
    input  wire [11:0] sensor_adc_left,
    input  wire        sensor_valid_left,
    input  wire [11:0] sensor_adc_right,
    input  wire        sensor_valid_right,

    // Camera features (from DVP capture, latched in AXI wrapper)
    input  wire [7:0]  cam_y_mean,
    input  wire [7:0]  cam_edge_count,
    input  wire [7:0]  cam_u_mean,
    input  wire        cam_valid,

    // Software familiarity override
    input  wire [7:0]  sw_familiarity,
    input  wire        sw_fam_enable,

    // Software Krimelack commit (for turntable capture)
    input  wire        sw_krim_commit,

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
    // 73 trits = 146 bits: 8 input strands × 8 trits + 6 settling + 3 decision
    output wire [145:0] loom_state,
    output wire [6:0]  n_effective,
    output wire [7:0]  omega,

    // Krimelack status
    output wire [5:0]  krimelack_count,
    output wire [7:0]  krimelack_score,
    output wire        krimelack_recall_valid,
    output wire        krimelack_commit_accepted,
    output wire        krimelack_commit_rejected,

    // Debug: raw steer field value (signed 16-bit)
    output wire signed [31:0] debug_steer_field
);

    // DSF outputs — not driven, no UF pipeline in ArcLoom
    // These ports remain for AXI wrapper compatibility
    assign dsf_safe_mode = 1'b0;
    assign dsf_valid = 1'b0;
    assign dsf_D = 2'b00;
    assign dsf_R_rev = 1'b0;

    // ================================================================
    // BSIL-BT: Full Balanced Ternary Sensor Encoding (3 sensors)
    // 8 trits per strand = 16 bits. Preserves full ADC gradient.
    // ================================================================
    wire [15:0] front_dist, front_dir, front_accel;
    wire        front_bsil_valid;

    arcloom_bsil_bt #(.N_TRITS(8), .BASELINE(12'd80)) bsil_front (
        .clk(clk), .rst_n(rst_n),
        .adc_value(sensor_adc_front), .adc_valid(sensor_valid_front),
        .bt_distance(front_dist), .bt_direction(front_dir),
        .bt_acceleration(front_accel), .out_valid(front_bsil_valid)
    );

    wire [15:0] left_dist, left_dir, left_accel;
    wire        left_bsil_valid;

    arcloom_bsil_bt #(.N_TRITS(8), .BASELINE(12'd111)) bsil_left (
        .clk(clk), .rst_n(rst_n),
        .adc_value(sensor_adc_left), .adc_valid(sensor_valid_left),
        .bt_distance(left_dist), .bt_direction(left_dir),
        .bt_acceleration(left_accel), .out_valid(left_bsil_valid)
    );

    wire [15:0] right_dist, right_dir, right_accel;
    wire        right_bsil_valid;

    arcloom_bsil_bt #(.N_TRITS(8), .BASELINE(12'd144)) bsil_right (
        .clk(clk), .rst_n(rst_n),
        .adc_value(sensor_adc_right), .adc_valid(sensor_valid_right),
        .bt_distance(right_dist), .bt_direction(right_dir),
        .bt_acceleration(right_accel), .out_valid(right_bsil_valid)
    );

    // ================================================================
    // BSIL-BT: Camera Feature Encoding (3 features)
    // 8-bit features zero-extended to 12-bit for BSIL-BT input.
    // Baselines are starting values — DSF-AI hw-derive will refine.
    // Camera features only produce distance (magnitude from baseline),
    // not direction or acceleration — those are IR sensor concepts.
    // ================================================================
    wire [15:0] cam_y_dist, cam_y_dir, cam_y_accel;
    wire        cam_y_valid;

    arcloom_bsil_bt #(.N_TRITS(8), .BASELINE(12'd120)) bsil_cam_y (
        .clk(clk), .rst_n(rst_n),
        .adc_value({4'd0, cam_y_mean}), .adc_valid(cam_valid),
        .bt_distance(cam_y_dist), .bt_direction(cam_y_dir),
        .bt_acceleration(cam_y_accel), .out_valid(cam_y_valid)
    );

    wire [15:0] cam_edge_dist, cam_edge_dir, cam_edge_accel;
    wire        cam_edge_valid;

    arcloom_bsil_bt #(.N_TRITS(8), .BASELINE(12'd80)) bsil_cam_edge (
        .clk(clk), .rst_n(rst_n),
        .adc_value({4'd0, cam_edge_count}), .adc_valid(cam_valid),
        .bt_distance(cam_edge_dist), .bt_direction(cam_edge_dir),
        .bt_acceleration(cam_edge_accel), .out_valid(cam_edge_valid)
    );

    wire [15:0] cam_u_dist, cam_u_dir, cam_u_accel;
    wire        cam_u_valid;

    arcloom_bsil_bt #(.N_TRITS(8), .BASELINE(12'd128)) bsil_cam_u (
        .clk(clk), .rst_n(rst_n),
        .adc_value({4'd0, cam_u_mean}), .adc_valid(cam_valid),
        .bt_distance(cam_u_dist), .bt_direction(cam_u_dir),
        .bt_acceleration(cam_u_accel), .out_valid(cam_u_valid)
    );

    // ================================================================
    // Damped Familiarity: coupling barrier on feedback path
    // Match score changes must exceed FAM_DEADZONE to propagate.
    // This prevents oscillation — small score fluctuations are absorbed.
    // Same physics as the SPPU dead zone, applied to the feedback itself.
    // ================================================================
    localparam [7:0] FAM_DEADZONE = 8'd15;  // barrier for familiarity changes

    reg [7:0] damped_fam;
    reg [7:0] prev_match_score;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            damped_fam       <= 8'd0;
            prev_match_score <= 8'd0;
        end else begin
            prev_match_score <= krimelack_score;
            // Only update familiarity when score change exceeds barrier
            if (krimelack_score > prev_match_score + FAM_DEADZONE ||
                prev_match_score > krimelack_score + FAM_DEADZONE) begin
                damped_fam <= krimelack_score >> 2;  // scaled as before
            end
        end
    end

    // Familiarity source: Python override > damped hardware > zero
    wire [7:0] active_familiarity = sw_fam_enable ? sw_familiarity : damped_fam;

    // ================================================================
    // SPPU: 8-trit Loom Fabric (COMBINATIONAL — NO CLOCK)
    // 5 input strands × 8 trits + 2 settling × 3 + 1 decision × 3
    // ================================================================
    arcloom_sppu sppu_inst (
        .in_front_dist(front_dist),
        .in_front_dir(front_dir),
        .in_front_accel(front_accel),
        .in_left_dist(left_dist),
        .in_right_dist(right_dist),
        .in_cam_y(cam_y_dist),
        .in_cam_edge(cam_edge_dist),
        .in_cam_u(cam_u_dist),
        .familiarity(active_familiarity),
        .ext_h_ctx(16'd0),
        .ext_h_mmtm(16'd0),
        .ext_h_steer(16'd0),
        .ext_h_speed(-16'd800),          // Tilted potential well: null trits contribute zero, bias tilts toward forward
        .ext_h_conf(16'd0),
        .loom_state(loom_state),
        .decision_steer(decision_steer),
        .decision_speed(decision_speed),
        .decision_conf(decision_conf),
        .field_ctx_0(), .field_ctx_1(), .field_ctx_2(),
        .field_mmtm_0(), .field_mmtm_1(), .field_mmtm_2(),
        .field_dcsn_0(debug_steer_field), .field_dcsn_1(), .field_dcsn_2()
    );

    // ================================================================
    // Krimelack: Structural Memory (CLOCKED)
    // ================================================================
    // Commit trigger: structural_lock from L6.
    //   When the loom state has collapsed (enough trits non-null),
    //   the state is stable and worth remembering.
    //
    // Uncertainty: derived from L6 n_effective.
    //   More null trits = more uncertain = higher u_star.
    //   n_effective is 0-73. Scale: u_star = n_effective/73 in 16.16.
    //   Approximation: n_effective << 10 (÷1024 ≈ ÷73 within factor of ~14x)
    //   This overestimates u_star, making commits harder. Acceptable — conservative.
    //
    // Resonance: derived from L6 omega (confinement ratio).
    //   High omega = many trits collapsed = high resonance.
    //   omega is 0-255 (scaled). resonance = omega << 8 as 16.16.
    //
    // Safe mode: none. Krimelack gates itself via its own thresholds.
    // ================================================================
    wire [47:0] recalled_motif;

    // Uncertainty from dimensional freedom: more null trits = more uncertain
    wire [31:0] u_star_from_l6 = {15'd0, n_effective, 10'd0};

    // Resonance from confinement: high omega = high resonance
    wire [31:0] resonance_from_l6 = {16'd0, omega, 8'd0};

    arcloom_krimelack #(.TRIT_WIDTH(48), .DEPTH(32)) krimelack_inst (
        .clk(clk), .rst_n(rst_n),
        .commit_request(structural_lock),
        .force_commit(sw_krim_commit),
        .state_in(loom_state[47:0]),
        .u_star(u_star_from_l6),
        .resonance(resonance_from_l6),
        .safe_mode(1'b0),
        .query(loom_state[47:0]),
        .best_match(recalled_motif),
        .match_score(krimelack_score),
        .recall_valid(krimelack_recall_valid),
        .motif_count(krimelack_count),
        .commit_accepted(krimelack_commit_accepted),
        .commit_rejected(krimelack_commit_rejected)
    );

    // ================================================================
    // L6: Topological Constraint Layer (COMBINATIONAL)
    // ArcLoom's own layer — observes dimensional exhaustion.
    // 73 trits, knee at 73/e ≈ 26.9 → KNEE=27
    // SL-1 fires when 46+ of 73 trits are non-null
    // Pure observer — no external gating, no TFE dependencies.
    // ================================================================
    arcloom_l6_tcl #(.N_TRITS(73), .KNEE(27)) l6_inst (
        .loom_state(loom_state),
        .disruption_active(1'b0),
        .recovery_pending(1'b0),
        .structural_lock(structural_lock),
        .n_effective(n_effective),
        .n_collapsed(),
        .omega(omega)
    );

endmodule
