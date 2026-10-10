// ============================================================
// ArcLoom SPPU — 9-Strand Kinematic Balanced Ternary Coupling
// ============================================================
//
// Pure Physical Substrate: 3 Distance Sensors × 3 Kinematic Orders
//
// 9 input strands (72 trits total = 144 bits):
//   [0] front_dist       Front distance (0th order / displacement D_k)
//   [1] front_dir        Front direction (1st order / velocity M_k)
//   [2] front_accel      Front acceleration (2nd order / curvature)
//   [3] left_dist        Left distance (0th order / displacement)
//   [4] left_dir         Left direction (1st order / velocity)
//   [5] left_accel       Left acceleration (2nd order / curvature)
//   [6] right_dist       Right distance (0th order / displacement)
//   [7] right_dir        Right direction (1st order / velocity)
//   [8] right_accel      Right acceleration (2nd order / curvature)
//
// Weights are exact 3^i positional values:
// [2187, 729, 243, 81, 27, 9, 3, 1]
// The weighted sum reconstructs the structural continuum from its
// balanced ternary encoding with zero loss and zero heuristics.
//
// 16-bit signed weights. 32-bit accumulators.
// Per-field dead zones in ADC units.
//
// NO clock. NO reg. Purely combinational.
// ============================================================

module arcloom_sppu #(
    // 72 input trits × 16 bits = 1152 bits per context/momentum field
    // 78 decision inputs (72 input + 6 settling) × 16 bits = 1248 bits

    // Context weights: all 9 kinematic strands reconstruct with 3^i
    parameter [1151:0] W_CTX_0 = {
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [8] right_accel
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [7] right_dir
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [6] right_dist
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [5] left_accel
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [4] left_dir
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [3] left_dist
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [2] front_accel
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [1] front_dir
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1}, // [0] front_dist

    parameter [1151:0] W_CTX_1 = {
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1},

    parameter [1151:0] W_CTX_2 = {
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1},

    // Momentum weights: emphasizes directional motion (1st derivatives)
    parameter [1151:0] W_MMTM_0 = {
        16'd0,    16'd0,   16'd0,   16'd0,  16'd0,  16'd0, 16'd0, 16'd0,     // [8] right_accel
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [7] right_dir
        16'd729,  16'd243, 16'd81,  16'd27, 16'd9,  16'd3, 16'd1, 16'd0,     // [6] right_dist
        16'd0,    16'd0,   16'd0,   16'd0,  16'd0,  16'd0, 16'd0, 16'd0,     // [5] left_accel
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [4] left_dir
        16'd729,  16'd243, 16'd81,  16'd27, 16'd9,  16'd3, 16'd1, 16'd0,     // [3] left_dist
        16'd0,    16'd0,   16'd0,   16'd0,  16'd0,  16'd0, 16'd0, 16'd0,     // [2] front_accel
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,   // [1] front_dir
        16'd729,  16'd243, 16'd81,  16'd27, 16'd9,  16'd3, 16'd1, 16'd0},   // [0] front_dist

    parameter [1151:0] W_MMTM_1 = {
        16'd0,    16'd0,   16'd0,   16'd0,  16'd0,  16'd0, 16'd0, 16'd0,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd729,  16'd243, 16'd81,  16'd27, 16'd9,  16'd3, 16'd1, 16'd0,
        16'd0,    16'd0,   16'd0,   16'd0,  16'd0,  16'd0, 16'd0, 16'd0,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd729,  16'd243, 16'd81,  16'd27, 16'd9,  16'd3, 16'd1, 16'd0,
        16'd0,    16'd0,   16'd0,   16'd0,  16'd0,  16'd0, 16'd0, 16'd0,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd729,  16'd243, 16'd81,  16'd27, 16'd9,  16'd3, 16'd1, 16'd0},

    parameter [1151:0] W_MMTM_2 = {
        16'd0,    16'd0,   16'd0,   16'd0,  16'd0,  16'd0, 16'd0, 16'd0,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd729,  16'd243, 16'd81,  16'd27, 16'd9,  16'd3, 16'd1, 16'd0,
        16'd0,    16'd0,   16'd0,   16'd0,  16'd0,  16'd0, 16'd0, 16'd0,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd729,  16'd243, 16'd81,  16'd27, 16'd9,  16'd3, 16'd1, 16'd0,
        16'd0,    16'd0,   16'd0,   16'd0,  16'd0,  16'd0, 16'd0, 16'd0,
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,
        16'd729,  16'd243, 16'd81,  16'd27, 16'd9,  16'd3, 16'd1, 16'd0},

    // Decision weights: 78 inputs (72 afferent + 6 settling) × 16 bits = 1248 bits
    //
    // DCSN_0 = STEER: Left repulsion vs Right repulsion
    parameter [1247:0] W_DCSN_0 = {
        16'd0, 16'd0, 16'd0,                                                          // momentum
        16'd0, 16'd0, 16'd0,                                                          // context
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,                       // [8] right_accel
        -16'd729, -16'd243, -16'd81, -16'd27, -16'd9, -16'd3, -16'd1, 16'd0,         // [7] right_dir (neg)
        -16'd2187, -16'd729, -16'd243, -16'd81, -16'd27, -16'd9, -16'd3, -16'd1,     // [6] right_dist (neg)
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,                       // [5] left_accel
        16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1, 16'd0,               // [4] left_dir (pos)
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,             // [3] left_dist (pos)
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,                       // [2] front_accel
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,                       // [1] front_dir
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0},                     // [0] front_dist

    // DCSN_1 = SPEED: Front obstacle repulsion + direction velocity penalty
    parameter [1247:0] W_DCSN_1 = {
        16'd0, 16'd0, 16'd0,                                                          // momentum
        16'd0, 16'd0, 16'd0,                                                          // context
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,                       // [8] right_accel
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,                       // [7] right_dir
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,                       // [6] right_dist
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,                       // [5] left_accel
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,                       // [4] left_dir
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,                       // [3] left_dist
        16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0, 16'd0,                       // [2] front_accel
        -16'd1093, -16'd364, -16'd121, -16'd40, -16'd13, -16'd4, -16'd1, 16'd0,       // [1] front_dir (approaching adds reverse)
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1},            // [0] front_dist (close = reverse)

    // DCSN_2 = CONFIDENCE: Global structural cohesion across all 9 afferent strands
    parameter [1247:0] W_DCSN_2 = {
        16'd0, 16'd0, 16'd0,                                                          // momentum
        16'd0, 16'd0, 16'd0,                                                          // context
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,             // [8] right_accel
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,             // [7] right_dir
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,             // [6] right_dist
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,             // [5] left_accel
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,             // [4] left_dir
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,             // [3] left_dist
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,             // [2] front_accel
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1,             // [1] front_dir
        16'd2187, 16'd729, 16'd243, 16'd81, 16'd27, 16'd9, 16'd3, 16'd1},            // [0] front_dist

    // Per-field dead zones
    parameter signed [31:0] DZ_CTX   = 32'd500,
    parameter signed [31:0] DZ_MMTM  = 32'd500,
    parameter signed [31:0] DZ_STEER = 32'd250,
    parameter signed [31:0] DZ_SPEED = 32'd500,
    parameter signed [31:0] DZ_CONF  = 32'd1000
)(
    // NO CLOCK INPUT. Pure combinational physics.

    // 9 Kinematic Afferent Strands (9 × 16 bits = 144 bits = 72 trits)
    input  wire [15:0] in_front_dist,
    input  wire [15:0] in_front_dir,
    input  wire [15:0] in_front_accel,
    input  wire [15:0] in_left_dist,
    input  wire [15:0] in_left_dir,
    input  wire [15:0] in_left_accel,
    input  wire [15:0] in_right_dist,
    input  wire [15:0] in_right_dir,
    input  wire [15:0] in_right_accel,

    input  wire [7:0]  familiarity,

    input  wire signed [15:0] ext_h_ctx,
    input  wire signed [15:0] ext_h_mmtm,
    input  wire signed [15:0] ext_h_steer,
    input  wire signed [15:0] ext_h_speed,
    input  wire signed [15:0] ext_h_conf,

    // 81 trits = 162 bits: 9 afferent strands (72 trits) + 6 settling + 3 decision
    output wire [161:0] loom_state,

    output wire [1:0]  decision_steer,
    output wire [1:0]  decision_speed,
    output wire [1:0]  decision_conf,

    output wire signed [31:0] field_ctx_0,  field_ctx_1,  field_ctx_2,
    output wire signed [31:0] field_mmtm_0, field_mmtm_1, field_mmtm_2,
    output wire signed [31:0] field_dcsn_0, field_dcsn_1, field_dcsn_2
);

    // ================================================================
    // Pack 72 input trits (9 × 8 = 72 trits = 144 bits)
    // ================================================================
    wire [143:0] input_trits = {in_right_accel, in_right_dir, in_right_dist,
                                 in_left_accel,  in_left_dir,  in_left_dist,
                                 in_front_accel, in_front_dir, in_front_dist};

    // ================================================================
    // LEVEL 1: Context + Momentum (72 input trits each)
    // ================================================================
    wire [1:0] ctx_0, ctx_1, ctx_2;

    arcloom_local_field #(.N_INPUTS(72), .DEAD_ZONE(DZ_CTX)) ctx_field_0 (
        .coupled_trits(input_trits), .weights(W_CTX_0),
        .external_h(ext_h_ctx), .dead_zone_adj(familiarity),
        .trit_out(ctx_0), .field_value(field_ctx_0)
    );
    arcloom_local_field #(.N_INPUTS(72), .DEAD_ZONE(DZ_CTX)) ctx_field_1 (
        .coupled_trits(input_trits), .weights(W_CTX_1),
        .external_h(ext_h_ctx), .dead_zone_adj(familiarity),
        .trit_out(ctx_1), .field_value(field_ctx_1)
    );
    arcloom_local_field #(.N_INPUTS(72), .DEAD_ZONE(DZ_CTX)) ctx_field_2 (
        .coupled_trits(input_trits), .weights(W_CTX_2),
        .external_h(ext_h_ctx), .dead_zone_adj(familiarity),
        .trit_out(ctx_2), .field_value(field_ctx_2)
    );

    wire [1:0] mmtm_0, mmtm_1, mmtm_2;

    arcloom_local_field #(.N_INPUTS(72), .DEAD_ZONE(DZ_MMTM)) mmtm_field_0 (
        .coupled_trits(input_trits), .weights(W_MMTM_0),
        .external_h(ext_h_mmtm), .dead_zone_adj(familiarity),
        .trit_out(mmtm_0), .field_value(field_mmtm_0)
    );
    arcloom_local_field #(.N_INPUTS(72), .DEAD_ZONE(DZ_MMTM)) mmtm_field_1 (
        .coupled_trits(input_trits), .weights(W_MMTM_1),
        .external_h(ext_h_mmtm), .dead_zone_adj(familiarity),
        .trit_out(mmtm_1), .field_value(field_mmtm_1)
    );
    arcloom_local_field #(.N_INPUTS(72), .DEAD_ZONE(DZ_MMTM)) mmtm_field_2 (
        .coupled_trits(input_trits), .weights(W_MMTM_2),
        .external_h(ext_h_mmtm), .dead_zone_adj(familiarity),
        .trit_out(mmtm_2), .field_value(field_mmtm_2)
    );

    // ================================================================
    // LEVEL 2: Decision (72 input + 6 settling = 78 trits = 156 bits)
    // ================================================================
    wire [155:0] dcsn_sources = {mmtm_2, mmtm_1, mmtm_0,
                                  ctx_2, ctx_1, ctx_0,
                                  input_trits};

    wire [1:0] dcsn_0, dcsn_1, dcsn_2;

    arcloom_local_field #(.N_INPUTS(78), .DEAD_ZONE(DZ_STEER)) dcsn_field_0 (
        .coupled_trits(dcsn_sources), .weights(W_DCSN_0),
        .external_h(ext_h_steer), .dead_zone_adj(familiarity),
        .trit_out(dcsn_0), .field_value(field_dcsn_0)
    );
    arcloom_local_field #(.N_INPUTS(78), .DEAD_ZONE(DZ_SPEED)) dcsn_field_1 (
        .coupled_trits(dcsn_sources), .weights(W_DCSN_1),
        .external_h(ext_h_speed), .dead_zone_adj(familiarity),
        .trit_out(dcsn_1), .field_value(field_dcsn_1)
    );
    arcloom_local_field #(.N_INPUTS(78), .DEAD_ZONE(DZ_CONF)) dcsn_field_2 (
        .coupled_trits(dcsn_sources), .weights(W_DCSN_2),
        .external_h(ext_h_conf), .dead_zone_adj(familiarity),
        .trit_out(dcsn_2), .field_value(field_dcsn_2)
    );

    // ================================================================
    // Output: 81 trits = 162 bits
    // Order matches canonical read layout: Decision [5:0], Context [11:6],
    // Momentum [17:12], Afferents [161:18].
    // ================================================================
    assign loom_state = {in_right_accel, in_right_dir, in_right_dist,
                         in_left_accel,  in_left_dir,  in_left_dist,
                         in_front_accel, in_front_dir, in_front_dist,
                         mmtm_2, mmtm_1, mmtm_0,
                         ctx_2, ctx_1, ctx_0,
                         dcsn_2, dcsn_1, dcsn_0};

    assign decision_steer = dcsn_0;
    assign decision_speed = dcsn_1;
    assign decision_conf  = dcsn_2;

endmodule
