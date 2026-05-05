// DSF-AI Derived Coupling Weights + BSIL Thresholds
// Sharp GP2Y0A41SK0F (3x, front/left/right)
// 2026-05-05 23:09:05
// UF-Core L0→L1→L2→L3→L4 (complete pipeline)
// Method: L4 DSF → coupling weights; L1 gates → BSIL thresholds

    // ---- DSF-AI Derived Coupling Weights (8-trit architecture) ----
    // Generated: 2026-05-05 23:09:05
    // Sensor: Sharp GP2Y0A41SK0F (3x, front/left/right)
    // Kernel: UF-Core L0→L1→L2→L3→L4 (complete pipeline)
    // Architecture: 5 strands × 8 trits = 40 input trits
    // Trit taper: 3^i positional significance (MSB=full weight, LSB=15%)
    // Tool: tools/derive_sppu_weights.py

    // CTX_0: front_dist, front_dir, front_accel, left_dist, right_dist
    parameter [319:0] W_CTX_0 = {8'd13, 8'd4, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd13, 8'd4, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd13, 8'd4, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd13, 8'd4, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd13, 8'd4, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1},
    // CTX_1: front_dist, front_dir, front_accel, left_dist, right_dist
    parameter [319:0] W_CTX_1 = {8'd13, 8'd4, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd13, 8'd4, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd13, 8'd4, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd13, 8'd4, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd13, 8'd4, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1},
    // CTX_2: front_dist, front_dir, front_accel, left_dist, right_dist
    parameter [319:0] W_CTX_2 = {8'd13, 8'd4, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd13, 8'd4, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd13, 8'd4, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd13, 8'd4, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd13, 8'd4, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1},

    // MMTM_0: front_dist, front_dir, front_accel, left_dist, right_dist
    parameter [319:0] W_MMTM_0 = {8'd8, 8'd2, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd8, 8'd2, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd8, 8'd2, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd14, 8'd4, 8'd2, 8'd2, 8'd2, 8'd2, 8'd2, 8'd2, 8'd8, 8'd2, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1},
    // MMTM_1: front_dist, front_dir, front_accel, left_dist, right_dist
    parameter [319:0] W_MMTM_1 = {8'd8, 8'd2, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd8, 8'd2, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd8, 8'd2, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd14, 8'd4, 8'd2, 8'd2, 8'd2, 8'd2, 8'd2, 8'd2, 8'd8, 8'd2, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1},
    // MMTM_2: front_dist, front_dir, front_accel, left_dist, right_dist
    parameter [319:0] W_MMTM_2 = {8'd8, 8'd2, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd8, 8'd2, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd8, 8'd2, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd14, 8'd4, 8'd2, 8'd2, 8'd2, 8'd2, 8'd2, 8'd2, 8'd8, 8'd2, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1},

    // DCSN_0 = STEER
    //   front_dist: [0, 0, 0, 0, 0, 0, 0, 0]
    //   front_dir: [0, 0, 0, 0, 0, 0, 0, 0]
    //   front_accel: [0, 0, 0, 0, 0, 0, 0, 0]
    //   left_dist: [4, 4, 4, 4, 4, 4, 11, 33]
    //   right_dist: [-5, -5, -5, -5, -5, -5, -12, -38]
    //   context: [0, 0, 0]  momentum: [0, 0, 0]
    parameter [367:0] W_DCSN_0 = {8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'hDA, 8'hF4, 8'hFB, 8'hFB, 8'hFB, 8'hFB, 8'hFB, 8'hFB, 8'd33, 8'd11, 8'd4, 8'd4, 8'd4, 8'd4, 8'd4, 8'd4, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0},

    // DCSN_1 = SPEED
    //   front_dist: [5, 5, 5, 5, 5, 5, 11, 35]
    //   front_dir: [2, 2, 2, 2, 2, 2, 5, 15]
    //   front_accel: [1, 1, 1, 1, 1, 1, 1, 4]
    //   left_dist: [1, 1, 1, 1, 1, 1, 1, 5]
    //   right_dist: [1, 1, 1, 1, 1, 1, 2, 6]
    //   context: [2, 2, 2]  momentum: [3, 3, 3]
    parameter [367:0] W_DCSN_1 = {8'd3, 8'd3, 8'd3, 8'd2, 8'd2, 8'd2, 8'd6, 8'd2, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd5, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd4, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd15, 8'd5, 8'd2, 8'd2, 8'd2, 8'd2, 8'd2, 8'd2, 8'd35, 8'd11, 8'd5, 8'd5, 8'd5, 8'd5, 8'd5, 8'd5},

    // DCSN_2 = CONFIDENCE
    //   front_dist: [1, 1, 1, 1, 1, 1, 3, 11]
    //   front_dir: [0, 0, 0, 0, 0, 0, 0, 0]
    //   front_accel: [0, 0, 0, 0, 0, 0, 0, 0]
    //   left_dist: [1, 1, 1, 1, 1, 1, 2, 7]
    //   right_dist: [1, 1, 1, 1, 1, 1, 2, 6]
    //   context: [1, 1, 1]  momentum: [2, 2, 2]
    parameter [367:0] W_DCSN_2 = {8'd2, 8'd2, 8'd2, 8'd1, 8'd1, 8'd1, 8'd6, 8'd2, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd7, 8'd2, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd11, 8'd3, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1, 8'd1}


// ---- DSF-AI Derived BSIL Thresholds ----
// From L1 structural gate boundaries
// Gap between low/high = structural ambiguity (dead zone)

// front sensor thresholds:
//   coarse: low=446, high=584  (gap=138)
//   medium: low=619, high=818  (gap=199)
//   fine: low=1006, high=2406  (gap=1400)
parameter [11:0] THRESH_FRONT_COARSE_LO = 12'd446;
parameter [11:0] THRESH_FRONT_COARSE_HI = 12'd584;
parameter [11:0] THRESH_FRONT_MEDIUM_LO = 12'd619;
parameter [11:0] THRESH_FRONT_MEDIUM_HI = 12'd818;
parameter [11:0] THRESH_FRONT_FINE_LO = 12'd1006;
parameter [11:0] THRESH_FRONT_FINE_HI = 12'd2406;

// left sensor thresholds:
//   coarse: low=523, high=597  (gap=74)
//   medium: low=628, high=909  (gap=281)
//   fine: low=1002, high=2323  (gap=1321)
parameter [11:0] THRESH_LEFT_COARSE_LO = 12'd523;
parameter [11:0] THRESH_LEFT_COARSE_HI = 12'd597;
parameter [11:0] THRESH_LEFT_MEDIUM_LO = 12'd628;
parameter [11:0] THRESH_LEFT_MEDIUM_HI = 12'd909;
parameter [11:0] THRESH_LEFT_FINE_LO = 12'd1002;
parameter [11:0] THRESH_LEFT_FINE_HI = 12'd2323;

// right sensor thresholds:
//   coarse: low=411, high=530  (gap=119)
//   medium: low=577, high=820  (gap=243)
//   fine: low=974, high=2592  (gap=1618)
parameter [11:0] THRESH_RIGHT_COARSE_LO = 12'd411;
parameter [11:0] THRESH_RIGHT_COARSE_HI = 12'd530;
parameter [11:0] THRESH_RIGHT_MEDIUM_LO = 12'd577;
parameter [11:0] THRESH_RIGHT_MEDIUM_HI = 12'd820;
parameter [11:0] THRESH_RIGHT_FINE_LO = 12'd974;
parameter [11:0] THRESH_RIGHT_FINE_HI = 12'd2592;
