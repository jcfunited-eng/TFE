// DSF-AI Derived Coupling Weights
// Sharp GP2Y0A41SK0F (3x, front/left/right)
// 2026-05-04 00:19:16
// UF-Core L0→L1→L2→L3→L4 (complete pipeline)
// Method: L4 DSF 7-tuple geometry → coupling weights

    // ---- DSF-AI Derived Coupling Weights ----
    // Generated: 2026-05-04 00:19:16
    // Sensor: Sharp GP2Y0A41SK0F (3x, front/left/right)
    // Kernel: UF-Core L0→L1→L2→L3→L4 (complete pipeline)
    // Weights derived from L4 DSF 7-tuple geometry
    // Tool: tools/derive_sppu_weights.py

    parameter [119:0] W_CTX_0 = {8'd0, 8'd0, 8'd13, 8'd0, 8'd0, 8'd13, 8'd0, 8'd0, 8'd26, 8'd0, 8'd0, 8'd26, 8'd13, 8'd13, 8'd26},
    parameter [119:0] W_CTX_1 = {8'd0, 8'd13, 8'd0, 8'd0, 8'd13, 8'd0, 8'd0, 8'd18, 8'd0, 8'd0, 8'd26, 8'd0, 8'd13, 8'd26, 8'd13},
    parameter [119:0] W_CTX_2 = {8'd13, 8'd0, 8'd0, 8'd13, 8'd0, 8'd0, 8'd18, 8'd0, 8'd0, 8'd26, 8'd0, 8'd0, 8'd26, 8'd13, 8'd13},

    parameter [119:0] W_MMTM_0 = {8'd6, 8'd6, 8'd11, 8'd6, 8'd6, 8'd6, 8'd6, 8'd6, 8'd6, 8'd11, 8'd17, 8'd22, 8'd6, 8'd11, 8'd17},
    parameter [119:0] W_MMTM_1 = {8'd6, 8'd11, 8'd6, 8'd6, 8'd11, 8'd6, 8'd6, 8'd11, 8'd6, 8'd17, 8'd22, 8'd17, 8'd11, 8'd17, 8'd11},
    parameter [119:0] W_MMTM_2 = {8'd11, 8'd6, 8'd6, 8'd11, 8'd6, 8'd6, 8'd11, 8'd6, 8'd6, 8'd22, 8'd17, 8'd11, 8'd17, 8'd11, 8'd6},

    // DCSN_0 = STEER
    parameter [167:0] W_DCSN_0 = {8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd18, 8'd24, 8'd33, 8'd20, 8'd28, 8'd38, 8'd4, 8'd6, 8'd10, 8'd7, 8'd10, 8'd15},
    // DCSN_1 = SPEED
    parameter [167:0] W_DCSN_1 = {8'd19, 8'd26, 8'd35, 8'd8, 8'd11, 8'd15, 8'd2, 8'd3, 8'd4, 8'd5, 8'd5, 8'd5, 8'd6, 8'd6, 8'd6, 8'd10, 8'd15, 8'd10, 8'd15, 8'd20, 8'd15},
    // DCSN_2 = CONFIDENCE
    parameter [167:0] W_DCSN_2 = {8'd14, 8'd11, 8'd11, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd0, 8'd7, 8'd7, 8'd7, 8'd6, 8'd6, 8'd6, 8'd15, 8'd10, 8'd10, 8'd20, 8'd10, 8'd10}