// ============================================================
// ArcLoom SPPU — Single-Point Processing Unit
// ============================================================
//
// THIS IS THE KERNEL. Purely combinational. No clock.
//
// 8 strands x 3 trits = 24 trits = 48 wires.
//
// Input strands (5):
//   distance[3]      — from Sharp IR sensor via BSIL
//   direction[3]     — delta of distance
//   acceleration[3]  — second derivative
//   camera_edge[3]   — from USB camera via ARM BSIL encoder
//   camera_motion[3] — optical flow via ARM BSIL encoder
//
// Settling strands (3):
//   context[3]       — environmental assessment
//   momentum[3]      — trend/inertia
//   DECISION[3]      — steer/speed/confidence output
//
// The coupling weights ARE the program. Different weights =
// different solution. The SPPU is solution-agnostic.
//
// Trit encoding: 00=0 (null), 01=+1, 10=-1, 11=invalid
//
// NO clock. NO reg. Purely combinational.
// ============================================================

module arcloom_sppu #(
    // ---- DSF-AI Derived Weights ----
    // Source: Sharp GP2Y0A41SK0F calibration data
    // Derived by: UF kernel L0-L4 structural analysis (tools/derive_sppu_weights.py)
    // NOT hand-approximated. Structurally correct for this sensor.

    // ---- Context strand weights (15 inputs: 5 input strands x 3 trits) ----
    parameter [119:0] W_CTX_0 = {8'd0, 8'd0, 8'd10, 8'd0, 8'd0, 8'd10, 8'd0, 8'd0, 8'd30, 8'd0, 8'd0, 8'd10, 8'd5, 8'd5, 8'd10},
    parameter [119:0] W_CTX_1 = {8'd0, 8'd10, 8'd0, 8'd0, 8'd10, 8'd0, 8'd0, 8'd20, 8'd0, 8'd0, 8'd10, 8'd0, 8'd5, 8'd10, 8'd5},
    parameter [119:0] W_CTX_2 = {8'd10, 8'd0, 8'd0, 8'd10, 8'd0, 8'd0, 8'd20, 8'd0, 8'd0, 8'd10, 8'd0, 8'd0, 8'd10, 8'd5, 8'd5},

    // ---- Momentum strand weights (15 inputs) ----
    parameter [119:0] W_MMTM_0 = {8'd5, 8'd5, 8'd10, 8'd5, 8'd5, 8'd5, 8'd5, 8'd5, 8'd5, 8'd10, 8'd15, 8'd20, 8'd5, 8'd10, 8'd15},
    parameter [119:0] W_MMTM_1 = {8'd5, 8'd10, 8'd5, 8'd5, 8'd10, 8'd5, 8'd5, 8'd10, 8'd5, 8'd15, 8'd20, 8'd15, 8'd10, 8'd15, 8'd10},
    parameter [119:0] W_MMTM_2 = {8'd10, 8'd5, 8'd5, 8'd10, 8'd5, 8'd5, 8'd10, 8'd5, 8'd5, 8'd20, 8'd15, 8'd10, 8'd15, 8'd10, 8'd5},

    // ---- Decision strand weights (21 inputs: 5 input + 2 settling x 3 trits) ----
    // DCSN_0 = STEER: left/right differential only. Front has zero structural
    //   coupling to lateral direction (confirmed by L4 DSF analysis).
    //   Left close → steer +1 (turn right). Right close → steer -1 (turn left).
    parameter [167:0] W_DCSN_0 = {8'd0, 8'd0, 8'd0,       // distance — no steer (DSF-AI confirmed)
                                   8'd0, 8'd0, 8'd0,       // direction — no steer (DSF-AI confirmed)
                                   8'd0, 8'd0, 8'd0,       // accel — no steer (DSF-AI confirmed)
                                   8'd20, 8'd27, 8'd34,    // cam_edge (LEFT) — from L4 D_std
                                   8'd20, 8'd27, 8'd34,    // cam_motion (RIGHT) — from L4 D_std
                                   8'd5, 8'd5, 8'd10,      // context
                                   8'd5, 8'd10, 8'd15},    // momentum
    // DCSN_1 = SPEED: front distance dominates. Left/right moderate (slow near walls).
    //   Weight ratios from L4 structural responsiveness.
    parameter [167:0] W_DCSN_1 = {8'd24, 8'd34, 8'd40,    // distance — front dominates speed
                                   8'd9, 8'd12, 8'd15,     // direction — from L4 momentum
                                   8'd3, 8'd4, 8'd6,       // accel — from L4 curvature
                                   8'd10, 8'd10, 8'd10,    // cam_edge (LEFT) — side wall influence
                                   8'd10, 8'd10, 8'd10,    // cam_motion (RIGHT) — side wall influence
                                   8'd10, 8'd15, 8'd10,    // context
                                   8'd15, 8'd20, 8'd15},   // momentum
    // DCSN_2 = CONFIDENCE: from L4 breathing range and uncertainty.
    parameter [167:0] W_DCSN_2 = {8'd16, 8'd13, 8'd13,    // distance — from 1-U_mean
                                   8'd15, 8'd10, 8'd10,    // direction
                                   8'd10, 8'd10, 8'd5,     // accel
                                   8'd10, 8'd10, 8'd10,    // cam_edge (LEFT)
                                   8'd10, 8'd10, 8'd10,    // cam_motion (RIGHT)
                                   8'd15, 8'd10, 8'd10,    // context
                                   8'd20, 8'd10, 8'd10},   // momentum

    parameter [15:0] DEAD_ZONE = 16'd20
)(
    // NO CLOCK INPUT.

    // Input strands — 5 strands x 3 trits = 30 bits
    input  wire [5:0]  in_distance,
    input  wire [5:0]  in_direction,
    input  wire [5:0]  in_accel,
    input  wire [5:0]  in_cam_edge,
    input  wire [5:0]  in_cam_motion,

    // Familiarity feedback from krimelack (raises dead zone)
    input  wire [7:0]  familiarity,

    // External field bias (from UF pipeline DSF feedback)
    input  wire [7:0]  ext_h_ctx,
    input  wire [7:0]  ext_h_mmtm,
    input  wire [7:0]  ext_h_dcsn,

    // Output: full loom state (8 strands x 3 trits = 48 bits)
    output wire [47:0] loom_state,

    // Decision outputs
    output wire [1:0]  decision_steer,
    output wire [1:0]  decision_speed,
    output wire [1:0]  decision_conf,

    // Debug: raw field values
    output wire [15:0] field_ctx_0,  field_ctx_1,  field_ctx_2,
    output wire [15:0] field_mmtm_0, field_mmtm_1, field_mmtm_2,
    output wire [15:0] field_dcsn_0, field_dcsn_1, field_dcsn_2
);

    // ================================================================
    // Pack all 15 input trits (5 strands x 3 trits = 30 bits)
    // ================================================================
    wire [29:0] input_trits = {in_cam_motion, in_cam_edge,
                                in_accel, in_direction, in_distance};

    // ================================================================
    // LEVEL 1: Context + Momentum (parallel, from 5 input strands)
    // ================================================================
    wire [1:0] ctx_0, ctx_1, ctx_2;

    arcloom_local_field #(.N_INPUTS(15)) ctx_field_0 (
        .coupled_trits(input_trits), .weights(W_CTX_0),
        .external_h(ext_h_ctx), .dead_zone_adj(familiarity),
        .trit_out(ctx_0), .field_value(field_ctx_0)
    );
    arcloom_local_field #(.N_INPUTS(15)) ctx_field_1 (
        .coupled_trits(input_trits), .weights(W_CTX_1),
        .external_h(ext_h_ctx), .dead_zone_adj(familiarity),
        .trit_out(ctx_1), .field_value(field_ctx_1)
    );
    arcloom_local_field #(.N_INPUTS(15)) ctx_field_2 (
        .coupled_trits(input_trits), .weights(W_CTX_2),
        .external_h(ext_h_ctx), .dead_zone_adj(familiarity),
        .trit_out(ctx_2), .field_value(field_ctx_2)
    );

    wire [1:0] mmtm_0, mmtm_1, mmtm_2;

    arcloom_local_field #(.N_INPUTS(15)) mmtm_field_0 (
        .coupled_trits(input_trits), .weights(W_MMTM_0),
        .external_h(ext_h_mmtm), .dead_zone_adj(familiarity),
        .trit_out(mmtm_0), .field_value(field_mmtm_0)
    );
    arcloom_local_field #(.N_INPUTS(15)) mmtm_field_1 (
        .coupled_trits(input_trits), .weights(W_MMTM_1),
        .external_h(ext_h_mmtm), .dead_zone_adj(familiarity),
        .trit_out(mmtm_1), .field_value(field_mmtm_1)
    );
    arcloom_local_field #(.N_INPUTS(15)) mmtm_field_2 (
        .coupled_trits(input_trits), .weights(W_MMTM_2),
        .external_h(ext_h_mmtm), .dead_zone_adj(familiarity),
        .trit_out(mmtm_2), .field_value(field_mmtm_2)
    );

    // ================================================================
    // LEVEL 2: Decision (from all 7 strands = 21 trits = 42 bits)
    // ================================================================
    wire [41:0] dcsn_sources = {mmtm_2, mmtm_1, mmtm_0,
                                 ctx_2, ctx_1, ctx_0,
                                 in_cam_motion, in_cam_edge,
                                 in_accel, in_direction, in_distance};

    wire [1:0] dcsn_0, dcsn_1, dcsn_2;

    arcloom_local_field #(.N_INPUTS(21)) dcsn_field_0 (
        .coupled_trits(dcsn_sources), .weights(W_DCSN_0),
        .external_h(ext_h_dcsn), .dead_zone_adj(familiarity),
        .trit_out(dcsn_0), .field_value(field_dcsn_0)
    );
    arcloom_local_field #(.N_INPUTS(21)) dcsn_field_1 (
        .coupled_trits(dcsn_sources), .weights(W_DCSN_1),
        .external_h(ext_h_dcsn), .dead_zone_adj(familiarity),
        .trit_out(dcsn_1), .field_value(field_dcsn_1)
    );
    arcloom_local_field #(.N_INPUTS(21)) dcsn_field_2 (
        .coupled_trits(dcsn_sources), .weights(W_DCSN_2),
        .external_h(ext_h_dcsn), .dead_zone_adj(familiarity),
        .trit_out(dcsn_2), .field_value(field_dcsn_2)
    );

    // ================================================================
    // Output: 8 strands = 48 bits
    // ================================================================
    assign loom_state = {dcsn_2, dcsn_1, dcsn_0,           // [47:42] decision
                         mmtm_2, mmtm_1, mmtm_0,           // [41:36] momentum
                         ctx_2, ctx_1, ctx_0,               // [35:30] context
                         in_cam_motion, in_cam_edge,        // [29:18] camera
                         in_accel, in_direction, in_distance}; // [17:0] sensor

    assign decision_steer = dcsn_0;
    assign decision_speed = dcsn_1;
    assign decision_conf  = dcsn_2;

endmodule
