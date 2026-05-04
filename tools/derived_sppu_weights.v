// DSF-AI Derived Coupling Weights
// Sharp GP2Y0A41SK0F (3x, front/left/right)
// 2026-05-04 00:10:57
// Kernel: UF-Core L0-L4

    // ---- DSF-AI Derived Coupling Weights ----
    // Generated: 2026-05-04 00:10:57
    // Sensor: Sharp GP2Y0A41SK0F (3x, front/left/right)
    // Kernel: UF-Core L0-L4 structural analysis
    // Tool: tools/derive_sppu_weights.py
    // THIS IS NOT HAND-APPROXIMATED. These weights are
    // structurally derived from the sensor's physics.

    parameter [119:0] W_CTX_0 = {8'd0, 8'd0, 8'd10, 8'd0, 8'd0, 8'd10, 8'd0, 8'd0, 8'd30, 8'd0, 8'd0, 8'd10, 8'd5, 8'd5, 8'd10},
    parameter [119:0] W_CTX_1 = {8'd0, 8'd10, 8'd0, 8'd0, 8'd10, 8'd0, 8'd0, 8'd20, 8'd0, 8'd0, 8'd10, 8'd0, 8'd5, 8'd10, 8'd5},
    parameter [119:0] W_CTX_2 = {8'd10, 8'd0, 8'd0, 8'd10, 8'd0, 8'd0, 8'd20, 8'd0, 8'd0, 8'd10, 8'd0, 8'd0, 8'd10, 8'd5, 8'd5},

    parameter [119:0] W_MMTM_0 = {8'd5, 8'd5, 8'd10, 8'd5, 8'd5, 8'd5, 8'd5, 8'd5, 8'd5, 8'd10, 8'd15, 8'd20, 8'd5, 8'd10, 8'd15},
    parameter [119:0] W_MMTM_1 = {8'd5, 8'd10, 8'd5, 8'd5, 8'd10, 8'd5, 8'd5, 8'd10, 8'd5, 8'd15, 8'd20, 8'd15, 8'd10, 8'd15, 8'd10},
    parameter [119:0] W_MMTM_2 = {8'd10, 8'd5, 8'd5, 8'd10, 8'd5, 8'd5, 8'd10, 8'd5, 8'd5, 8'd20, 8'd15, 8'd10, 8'd15, 8'd10, 8'd5},

    // DCSN_0 = STEER
    parameter [167:0] W_DCSN_0 = {8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd20, 8'd27, 8'd34, 8'd19, 8'd26, 8'd33, 8'd5, 8'd5, 8'd10, 8'd5, 8'd10, 8'd15},
    // DCSN_1 = SPEED
    parameter [167:0] W_DCSN_1 = {8'd24, 8'd34, 8'd40, 8'd9, 8'd12, 8'd15, 8'd3, 8'd4, 8'd6, 8'd9, 8'd9, 8'd9, 8'd9, 8'd9, 8'd9, 8'd10, 8'd15, 8'd10, 8'd15, 8'd20, 8'd15},
    // DCSN_2 = CONFIDENCE
    parameter [167:0] W_DCSN_2 = {8'd16, 8'd13, 8'd13, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd10, 8'd10, 8'd10, 8'd10, 8'd10, 8'd10, 8'd10, 8'd15, 8'd10, 8'd15, 8'd20, 8'd15}