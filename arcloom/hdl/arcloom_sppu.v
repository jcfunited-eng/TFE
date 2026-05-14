// ============================================================
// ArcLoom SPPU — 12-strand, 8-trit, 3^i positional coupling
// ============================================================
//
// The coupling IS MathLoom. Weights are 3^i positional values
// [1, 3, 9, 27, 81, 243, 729, 2187]. The weighted sum
// reconstructs the original number from its balanced ternary
// encoding. No information loss. No cancellation.
//
// 12 input strands: 5 IR sensor + 7 camera vision
//   [0]  front_dist       IR front distance
//   [1]  front_dir        IR front direction (1st derivative)
//   [2]  front_accel      IR front acceleration (2nd derivative)
//   [3]  left_dist        IR left distance
//   [4]  right_dist       IR right distance
//   [5]  cam_y_upper      Camera Y mean upper half (owl trick)
//   [6]  cam_y_lower      Camera Y mean lower half (owl trick)
//   [7]  cam_edge_upper   Camera edge count upper half
//   [8]  cam_edge_lower   Camera edge count lower half
//   [9]  cam_u_upper      Camera U chrominance upper half
//   [10] cam_u_lower      Camera U chrominance lower half
//   [11] cam_density      Structural density (high-edge lines per frame)
//
// 16-bit signed weights. 32-bit accumulator.
// Per-field dead zones in ADC units.
//
// NO clock. NO reg. Purely combinational.
// ============================================================

module arcloom_sppu #(
    // ---- 3^i positional weights (16-bit signed) ----
    // 96 inputs × 16 bits = 1536 bits per context/momentum field
    // 102 inputs × 16 bits = 1632 bits per decision field (96 + 6 settling)

    // Shorthand for one 8-trit strand of 3^i weights
    // P = positive 3^i:  [2187, 729, 243, 81, 27, 9, 3, 1]
    // N = negative 3^i:  [-2187, -729, -243, -81, -27, -9, -3, -1]
    // Z = zero (no coupling): [0, 0, 0, 0, 0, 0, 0, 0]

    // Context weights: all strands reconstruct with 3^i
    parameter [1535:0] W_CTX_0 = {
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [11] density
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [10] cam_u_lower
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [9]  cam_u_upper
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [8]  cam_edge_lower
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [7]  cam_edge_upper
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [6]  cam_y_lower
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [5]  cam_y_upper
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [4]  right_dist
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [3]  left_dist
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [2]  front_accel
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [1]  front_dir
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1},  // [0]  front_dist
    parameter [1535:0] W_CTX_1 = {
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1},
    parameter [1535:0] W_CTX_2 = {
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1},

    // Momentum weights: same as context
    parameter [1535:0] W_MMTM_0 = {
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1},
    parameter [1535:0] W_MMTM_1 = {
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1},
    parameter [1535:0] W_MMTM_2 = {
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1},

    // Decision weights: 102 inputs (96 input + 6 settling) × 16 bits = 1632 bits
    //
    // DCSN_0 = STEER: left vs right IR (camera zero for steer — DSF-AI may change)
    parameter [1631:0] W_DCSN_0 = {
        16'd0, 16'd0, 16'd0,                                                 // momentum
        16'd0, 16'd0, 16'd0,                                                 // context
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // [11] density
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // [10] cam_u_lower
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // [9]  cam_u_upper
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // [8]  cam_edge_lower
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // [7]  cam_edge_upper
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // [6]  cam_y_lower
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // [5]  cam_y_upper
        -16'd2187, -16'd729, -16'd243, -16'd81, -16'd27, -16'd9, -16'd3, -16'd1,  // [4] right (neg)
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [3]  left (pos)
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // [2]  front_accel
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // [1]  front_dir
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0},          // [0]  front_dist

    // DCSN_1 = SPEED: front distance + direction penalty. Camera zero for now.
    parameter [1631:0] W_DCSN_1 = {
        16'd0, 16'd0, 16'd0,                                                 // momentum
        16'd0, 16'd0, 16'd0,                                                 // context
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // [11] density
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // [10] cam_u_lower
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // [9]  cam_u_upper
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // [8]  cam_edge_lower
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // [7]  cam_edge_upper
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // [6]  cam_y_lower
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // [5]  cam_y_upper
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // [4]  right
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // [3]  left
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,           // [2]  front_accel
        -16'd1093, -16'd364, -16'd121, -16'd40, -16'd13, -16'd4, -16'd1, -16'd0,  // [1] front_dir (-0.5x)
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1}, // [0]  front_dist

    // DCSN_2 = CONFIDENCE: all strands reconstruct
    parameter [1631:0] W_DCSN_2 = {
        16'd0, 16'd0, 16'd0,                                                 // momentum
        16'd0, 16'd0, 16'd0,                                                 // context
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [11] density
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [10] cam_u_lower
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [9]  cam_u_upper
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [8]  cam_edge_lower
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [7]  cam_edge_upper
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [6]  cam_y_lower
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [5]  cam_y_upper
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [4]  right
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [3]  left
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [2]  front_accel
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [1]  front_dir
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1},  // [0]  front_dist

    // Per-field dead zones
    parameter signed [31:0] DZ_CTX   = 32'd500,
    parameter signed [31:0] DZ_MMTM  = 32'd500,
    parameter signed [31:0] DZ_STEER = 32'd250,
    parameter signed [31:0] DZ_SPEED = 32'd500,
    parameter signed [31:0] DZ_CONF  = 32'd1000
)(
    // NO CLOCK INPUT.

    // IR sensor strands (5 × 16 bits = 80 bits)
    input  wire [15:0] in_front_dist,
    input  wire [15:0] in_front_dir,
    input  wire [15:0] in_front_accel,
    input  wire [15:0] in_left_dist,
    input  wire [15:0] in_right_dist,

    // Camera strands — owl trick upper/lower + density (7 × 16 bits = 112 bits)
    input  wire [15:0] in_cam_y_upper,
    input  wire [15:0] in_cam_y_lower,
    input  wire [15:0] in_cam_edge_upper,
    input  wire [15:0] in_cam_edge_lower,
    input  wire [15:0] in_cam_u_upper,
    input  wire [15:0] in_cam_u_lower,
    input  wire [15:0] in_cam_density,

    input  wire [7:0]  familiarity,

    input  wire signed [15:0] ext_h_ctx,
    input  wire signed [15:0] ext_h_mmtm,
    input  wire signed [15:0] ext_h_steer,
    input  wire signed [15:0] ext_h_speed,
    input  wire signed [15:0] ext_h_conf,

    output wire [209:0] loom_state,  // 105 trits = 12×8 + 6 settling + 3 decision

    output wire [1:0]  decision_steer,
    output wire [1:0]  decision_speed,
    output wire [1:0]  decision_conf,

    output wire signed [31:0] field_ctx_0,  field_ctx_1,  field_ctx_2,
    output wire signed [31:0] field_mmtm_0, field_mmtm_1, field_mmtm_2,
    output wire signed [31:0] field_dcsn_0, field_dcsn_1, field_dcsn_2
);

    // ================================================================
    // Pack 96 input trits (12 × 8 = 192 bits)
    // ================================================================
    wire [191:0] input_trits = {in_cam_density,
                                 in_cam_u_lower, in_cam_u_upper,
                                 in_cam_edge_lower, in_cam_edge_upper,
                                 in_cam_y_lower, in_cam_y_upper,
                                 in_right_dist, in_left_dist,
                                 in_front_accel, in_front_dir, in_front_dist};

    // ================================================================
    // LEVEL 1: Context + Momentum (96 input trits each)
    // ================================================================
    wire [1:0] ctx_0, ctx_1, ctx_2;

    arcloom_local_field #(.N_INPUTS(96), .DEAD_ZONE(DZ_CTX)) ctx_field_0 (
        .coupled_trits(input_trits), .weights(W_CTX_0),
        .external_h(ext_h_ctx), .dead_zone_adj(familiarity),
        .trit_out(ctx_0), .field_value(field_ctx_0)
    );
    arcloom_local_field #(.N_INPUTS(96), .DEAD_ZONE(DZ_CTX)) ctx_field_1 (
        .coupled_trits(input_trits), .weights(W_CTX_1),
        .external_h(ext_h_ctx), .dead_zone_adj(familiarity),
        .trit_out(ctx_1), .field_value(field_ctx_1)
    );
    arcloom_local_field #(.N_INPUTS(96), .DEAD_ZONE(DZ_CTX)) ctx_field_2 (
        .coupled_trits(input_trits), .weights(W_CTX_2),
        .external_h(ext_h_ctx), .dead_zone_adj(familiarity),
        .trit_out(ctx_2), .field_value(field_ctx_2)
    );

    wire [1:0] mmtm_0, mmtm_1, mmtm_2;

    arcloom_local_field #(.N_INPUTS(96), .DEAD_ZONE(DZ_MMTM)) mmtm_field_0 (
        .coupled_trits(input_trits), .weights(W_MMTM_0),
        .external_h(ext_h_mmtm), .dead_zone_adj(familiarity),
        .trit_out(mmtm_0), .field_value(field_mmtm_0)
    );
    arcloom_local_field #(.N_INPUTS(96), .DEAD_ZONE(DZ_MMTM)) mmtm_field_1 (
        .coupled_trits(input_trits), .weights(W_MMTM_1),
        .external_h(ext_h_mmtm), .dead_zone_adj(familiarity),
        .trit_out(mmtm_1), .field_value(field_mmtm_1)
    );
    arcloom_local_field #(.N_INPUTS(96), .DEAD_ZONE(DZ_MMTM)) mmtm_field_2 (
        .coupled_trits(input_trits), .weights(W_MMTM_2),
        .external_h(ext_h_mmtm), .dead_zone_adj(familiarity),
        .trit_out(mmtm_2), .field_value(field_mmtm_2)
    );

    // ================================================================
    // LEVEL 2: Decision (96 input + 6 settling = 102 trits)
    // ================================================================
    wire [203:0] dcsn_sources = {mmtm_2, mmtm_1, mmtm_0,
                                  ctx_2, ctx_1, ctx_0,
                                  input_trits};

    wire [1:0] dcsn_0, dcsn_1, dcsn_2;

    arcloom_local_field #(.N_INPUTS(102), .DEAD_ZONE(DZ_STEER)) dcsn_field_0 (
        .coupled_trits(dcsn_sources), .weights(W_DCSN_0),
        .external_h(ext_h_steer), .dead_zone_adj(familiarity),
        .trit_out(dcsn_0), .field_value(field_dcsn_0)
    );
    arcloom_local_field #(.N_INPUTS(102), .DEAD_ZONE(DZ_SPEED)) dcsn_field_1 (
        .coupled_trits(dcsn_sources), .weights(W_DCSN_1),
        .external_h(ext_h_speed), .dead_zone_adj(familiarity),
        .trit_out(dcsn_1), .field_value(field_dcsn_1)
    );
    arcloom_local_field #(.N_INPUTS(102), .DEAD_ZONE(DZ_CONF)) dcsn_field_2 (
        .coupled_trits(dcsn_sources), .weights(W_DCSN_2),
        .external_h(ext_h_conf), .dead_zone_adj(familiarity),
        .trit_out(dcsn_2), .field_value(field_dcsn_2)
    );

    // ================================================================
    // Output: 105 trits = 210 bits
    // ================================================================
    assign loom_state = {in_front_dist, in_front_dir, in_front_accel,
                         in_left_dist, in_right_dist,
                         in_cam_y_upper, in_cam_y_lower,
                         in_cam_edge_upper, in_cam_edge_lower,
                         in_cam_u_upper, in_cam_u_lower,
                         in_cam_density,
                         mmtm_2, mmtm_1, mmtm_0,
                         ctx_2, ctx_1, ctx_0,
                         dcsn_2, dcsn_1, dcsn_0};

    assign decision_steer = dcsn_0;
    assign decision_speed = dcsn_1;
    assign decision_conf  = dcsn_2;

endmodule
