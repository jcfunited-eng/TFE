// ============================================================
// ArcLoom SPPU — 8-trit inputs, 3^i positional coupling
// ============================================================
//
// The coupling IS MathLoom. Weights are 3^i positional values
// [1, 3, 9, 27, 81, 243, 729, 2187]. The weighted sum
// reconstructs the original number from its balanced ternary
// encoding. No information loss. No cancellation.
//
// 8 input strands: 5 IR sensor + 3 camera vision
// 16-bit signed weights. 32-bit accumulator.
// Per-field dead zones in ADC units.
//
// NO clock. NO reg. Purely combinational.
// ============================================================

module arcloom_sppu #(
    // ---- 3^i positional weights (16-bit signed) ----
    // Each strand: [1, 3, 9, 27, 81, 243, 729, 2187] for reconstruction
    // Negative for right sensor steer (directional coupling)
    // Zero for strands with no coupling to that decision
    //
    // 8 input strands: 5 IR sensor + 3 camera
    //   [0]  front_dist    IR front distance
    //   [1]  front_dir     IR front direction (derivative)
    //   [2]  front_accel   IR front acceleration (2nd derivative)
    //   [3]  left_dist     IR left distance
    //   [4]  right_dist    IR right distance
    //   [5]  cam_y         Camera Y mean (brightness)
    //   [6]  cam_edge      Camera edge count (texture)
    //   [7]  cam_u         Camera U mean (chrominance)

    // Context strand weights (64 inputs × 16 bits = 1024 bits)
    parameter [1023:0] W_CTX_0 = {
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // cam_u
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // cam_edge
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // cam_y
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // right_dist
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // left_dist
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // front_accel
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // front_dir
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1},  // front_dist
    parameter [1023:0] W_CTX_1 = {
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1},
    parameter [1023:0] W_CTX_2 = {
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1},

    // Momentum strand weights (64 inputs × 16 bits = 1024 bits)
    parameter [1023:0] W_MMTM_0 = {
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1},
    parameter [1023:0] W_MMTM_1 = {
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1},
    parameter [1023:0] W_MMTM_2 = {
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1},

    // Decision strand weights (70 inputs × 16 bits = 1120 bits)
    // DCSN_0 = STEER: left reconstructs positive, right reconstructs negative
    // Camera has zero weight for steer — vision doesn't determine turn direction
    // Motor mapping is swapped (turn_r↔turn_l) to match physical wiring.
    parameter [1119:0] W_DCSN_0 = {
        16'd0, 16'd0, 16'd0,                                                 // momentum
        16'd0, 16'd0, 16'd0,                                                 // context
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // cam_u
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // cam_edge
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // cam_y
        -16'd2187, -16'd729, -16'd243, -16'd81, -16'd27, -16'd9, -16'd3, -16'd1,  // right (negative)
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // left (positive)
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // front_accel
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // front_dir
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0},          // front_dist

    // DCSN_1 = SPEED: front distance + direction penalty (-0.5x)
    // Camera has zero weight for speed — vision doesn't determine forward/reverse
    // DSF-AI hw-derive may change this later
    parameter [1119:0] W_DCSN_1 = {
        16'd0, 16'd0, 16'd0,                                                 // momentum
        16'd0, 16'd0, 16'd0,                                                 // context
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // cam_u
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // cam_edge
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // cam_y
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // right
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // left
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // front_accel
        -16'd1093, -16'd364, -16'd121, -16'd40, -16'd13, -16'd4, -16'd1, -16'd0,  // front_dir (-0.5x 3^i)
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1}, // front_dist

    // DCSN_2 = CONFIDENCE: all strands reconstruct (including camera)
    // More senses agreeing = higher confidence = more trits collapsing
    parameter [1119:0] W_DCSN_2 = {
        16'd0, 16'd0, 16'd0,                                                 // momentum
        16'd0, 16'd0, 16'd0,                                                 // context
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // cam_u
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // cam_edge
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // cam_y
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // right
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // left
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // front_accel
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // front_dir
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1}, // front_dist

    // Per-field dead zones (in ADC units)
    parameter signed [31:0] DZ_CTX  = 32'd500,
    parameter signed [31:0] DZ_MMTM = 32'd500,
    parameter signed [31:0] DZ_STEER = 32'd250,
    parameter signed [31:0] DZ_SPEED = 32'd500,
    parameter signed [31:0] DZ_CONF  = 32'd1000
)(
    // NO CLOCK INPUT.

    input  wire [15:0] in_front_dist,
    input  wire [15:0] in_front_dir,
    input  wire [15:0] in_front_accel,
    input  wire [15:0] in_left_dist,
    input  wire [15:0] in_right_dist,
    input  wire [15:0] in_cam_y,
    input  wire [15:0] in_cam_edge,
    input  wire [15:0] in_cam_u,

    input  wire [7:0]  familiarity,

    input  wire signed [15:0] ext_h_ctx,
    input  wire signed [15:0] ext_h_mmtm,
    input  wire signed [15:0] ext_h_steer,
    input  wire signed [15:0] ext_h_speed,
    input  wire signed [15:0] ext_h_conf,

    output wire [145:0] loom_state,  // 73 trits = 8 strands × 8 + 6 settling + 3 decision

    output wire [1:0]  decision_steer,
    output wire [1:0]  decision_speed,
    output wire [1:0]  decision_conf,

    output wire signed [31:0] field_ctx_0,  field_ctx_1,  field_ctx_2,
    output wire signed [31:0] field_mmtm_0, field_mmtm_1, field_mmtm_2,
    output wire signed [31:0] field_dcsn_0, field_dcsn_1, field_dcsn_2
);

    // ================================================================
    // Pack 64 input trits (8 × 8 = 128 bits)
    // ================================================================
    wire [127:0] input_trits = {in_cam_u, in_cam_edge, in_cam_y,
                                 in_right_dist, in_left_dist,
                                 in_front_accel, in_front_dir, in_front_dist};

    // ================================================================
    // LEVEL 1: Context + Momentum
    // ================================================================
    wire [1:0] ctx_0, ctx_1, ctx_2;

    arcloom_local_field #(.N_INPUTS(64), .DEAD_ZONE(DZ_CTX)) ctx_field_0 (
        .coupled_trits(input_trits), .weights(W_CTX_0),
        .external_h(ext_h_ctx), .dead_zone_adj(familiarity),
        .trit_out(ctx_0), .field_value(field_ctx_0)
    );
    arcloom_local_field #(.N_INPUTS(64), .DEAD_ZONE(DZ_CTX)) ctx_field_1 (
        .coupled_trits(input_trits), .weights(W_CTX_1),
        .external_h(ext_h_ctx), .dead_zone_adj(familiarity),
        .trit_out(ctx_1), .field_value(field_ctx_1)
    );
    arcloom_local_field #(.N_INPUTS(64), .DEAD_ZONE(DZ_CTX)) ctx_field_2 (
        .coupled_trits(input_trits), .weights(W_CTX_2),
        .external_h(ext_h_ctx), .dead_zone_adj(familiarity),
        .trit_out(ctx_2), .field_value(field_ctx_2)
    );

    wire [1:0] mmtm_0, mmtm_1, mmtm_2;

    arcloom_local_field #(.N_INPUTS(64), .DEAD_ZONE(DZ_MMTM)) mmtm_field_0 (
        .coupled_trits(input_trits), .weights(W_MMTM_0),
        .external_h(ext_h_mmtm), .dead_zone_adj(familiarity),
        .trit_out(mmtm_0), .field_value(field_mmtm_0)
    );
    arcloom_local_field #(.N_INPUTS(64), .DEAD_ZONE(DZ_MMTM)) mmtm_field_1 (
        .coupled_trits(input_trits), .weights(W_MMTM_1),
        .external_h(ext_h_mmtm), .dead_zone_adj(familiarity),
        .trit_out(mmtm_1), .field_value(field_mmtm_1)
    );
    arcloom_local_field #(.N_INPUTS(64), .DEAD_ZONE(DZ_MMTM)) mmtm_field_2 (
        .coupled_trits(input_trits), .weights(W_MMTM_2),
        .external_h(ext_h_mmtm), .dead_zone_adj(familiarity),
        .trit_out(mmtm_2), .field_value(field_mmtm_2)
    );

    // ================================================================
    // LEVEL 2: Decision (64 input + 6 settling = 70 trits)
    // ================================================================
    wire [139:0] dcsn_sources = {mmtm_2, mmtm_1, mmtm_0,
                                  ctx_2, ctx_1, ctx_0,
                                  in_cam_u, in_cam_edge, in_cam_y,
                                  in_right_dist, in_left_dist,
                                  in_front_accel, in_front_dir, in_front_dist};

    wire [1:0] dcsn_0, dcsn_1, dcsn_2;

    arcloom_local_field #(.N_INPUTS(70), .DEAD_ZONE(DZ_STEER)) dcsn_field_0 (
        .coupled_trits(dcsn_sources), .weights(W_DCSN_0),
        .external_h(ext_h_steer), .dead_zone_adj(familiarity),
        .trit_out(dcsn_0), .field_value(field_dcsn_0)
    );
    arcloom_local_field #(.N_INPUTS(70), .DEAD_ZONE(DZ_SPEED)) dcsn_field_1 (
        .coupled_trits(dcsn_sources), .weights(W_DCSN_1),
        .external_h(ext_h_speed), .dead_zone_adj(familiarity),
        .trit_out(dcsn_1), .field_value(field_dcsn_1)
    );
    arcloom_local_field #(.N_INPUTS(70), .DEAD_ZONE(DZ_CONF)) dcsn_field_2 (
        .coupled_trits(dcsn_sources), .weights(W_DCSN_2),
        .external_h(ext_h_conf), .dead_zone_adj(familiarity),
        .trit_out(dcsn_2), .field_value(field_dcsn_2)
    );

    // ================================================================
    // Output: 73 trits = 146 bits
    // ================================================================
    assign loom_state = {in_front_dist, in_front_dir, in_front_accel,
                         in_left_dist, in_right_dist,
                         in_cam_y, in_cam_edge, in_cam_u,
                         mmtm_2, mmtm_1, mmtm_0,
                         ctx_2, ctx_1, ctx_0,
                         dcsn_2, dcsn_1, dcsn_0};

    assign decision_steer = dcsn_0;
    assign decision_speed = dcsn_1;
    assign decision_conf  = dcsn_2;

endmodule
