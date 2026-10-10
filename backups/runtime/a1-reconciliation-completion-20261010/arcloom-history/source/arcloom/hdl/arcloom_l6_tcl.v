// ============================================================
// ArcLoom L6 — Topological Constraint Layer
// ============================================================
//
// L6-TCL Spec v1.0: Structural Inevitability Detection
//
// L6 does not compute. It OBSERVES.
// It watches the loom state and detects when dimensional
// exhaustion has collapsed the manifold to a singularity.
//
// The loom's coupling already DOES the exhaustion — each
// non-null trit is a collapsed degree of freedom. L6 just
// counts them and checks if the knee has been crossed.
//
// Structural Lock (SL-1) fires when:
//   n_effective < n_start / e
// AND no unrecovered exogenous disruption.
//
// For n_start = 18 trits: knee at 18/e ≈ 6.62
// So SL-1 fires when 12+ trits are non-null (n_eff < 7).
//
// Purely combinational. Read-only consumer of loom state.
// ============================================================

module arcloom_l6_tcl #(
    parameter N_TRITS    = 18,     // total trits in loom
    // n_start/e — the knee. For 18 trits: floor(18/2.71828) = 6
    // SL-1 fires when n_effective < KNEE, i.e., collapsed > N_TRITS - KNEE
    parameter KNEE       = 7       // n_start/e rounded up (conservative)
)(
    // NO CLOCK. Combinational.

    // Loom state (from SPPU)
    input  wire [2*N_TRITS-1:0] loom_state,

    // Exogenous disruption (from L0 boundary detector)
    input  wire                 disruption_active,
    // Hysteresis recovery (from UF pipeline)
    input  wire                 recovery_pending,

    // Outputs
    output wire                 structural_lock,  // SL-1
    output wire [6:0]           n_effective,      // residual degrees of freedom
    output wire [6:0]           n_collapsed,      // number of decided trits
    output wire [7:0]           omega             // Ω approximation [0,255] ≈ [0.0, 1.0]
);

    // ---- Count non-null trits (collapsed dimensions) ----
    // A trit is non-null if its 2-bit encoding is 01 (+1) or 10 (-1).
    // A trit is null (undecided) if 00.
    // Encoding 11 is invalid — treat as null.

    reg [6:0] collapsed;
    integer t;

    always @(loom_state) begin
        collapsed = 7'd0;
        for (t = 0; t < N_TRITS; t = t + 1) begin
            if (loom_state[2*t +: 2] == 2'b01 || loom_state[2*t +: 2] == 2'b10)
                collapsed = collapsed + 7'd1;
        end
    end

    // ---- Effective dimensionality ----
    wire [6:0] n_eff = N_TRITS - collapsed;

    // ---- Omega: geometric confinement ratio ----
    // Ω ≈ collapsed / N_TRITS, scaled to [0, 255]
    // This is a linear approximation of the volume ratio.
    // The actual Gamma-function ratio is steeper near the knee,
    // but for detection purposes the linear proxy suffices
    // because we only care about the threshold crossing.
    wire [14:0] omega_wide = (collapsed * 8'd255) / N_TRITS;
    wire [7:0]  omega_raw = omega_wide[7:0];

    // ---- Disruption gate ----
    // Any active exogenous disruption with pending recovery
    // multiplies Ω toward zero (prevents false lock).
    wire disruption_gate = disruption_active & recovery_pending;

    // ---- Structural Lock (SL-1) ----
    // Fires when:
    //   n_effective < KNEE (dimensional exhaustion)
    //   AND no disruption blocking
    assign structural_lock = (n_eff < KNEE) & ~disruption_gate;

    // ---- Outputs ----
    assign n_effective = n_eff;
    assign n_collapsed = collapsed;
    assign omega       = disruption_gate ? 8'd0 : omega_raw;

endmodule
