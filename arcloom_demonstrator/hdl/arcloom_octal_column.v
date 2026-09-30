// =============================================================================
// ArcLoom 8-Column Balanced Octet Core — Synthesizable Verilog RTL
// Target: Xilinx Zynq-7020 (PYNQ-Z2) @ 125 MHz
// Probing Instrument: Siglent SDS1104X-E 4-Channel Oscilloscope (Pmod A Header)
//
// 8 Functional Cortical Columns:
//   Col 0 (V1): Optical Foveal Disc
//   Col 1 (V2): Optical Edge / Spatial Angle
//   Col 2 (A1): Cochlear Formant Resonance
//   Col 3 (A2): Cochlear Pitch / Envelope
//   Col 4 (S1): Somatosensory Palmar Contact
//   Col 5 (S2): Somatosensory Barrier Stress
//   Col 6 (M1): Motor Airway Vocal Valve
//   Col 7 (M2): Motor Locomotion Stride / Steer
//
// 6 Laminar Layers per Column:
//   L1:   Apical Dendrite / UF Kernel Top-Down Bias (D_k, M_k, P_k, B_k, S_UF)
//   L2/3: Horizontal Associative Fasciculi (Inter-column Yield Bridges)
//   L4:   Sensory Input Gate (Afferent Transduction)
//   L5:   Deep Efferent / Recurrent Spatial Potential Well
//   L6:   Feedback Gating / Efferent Invariant Lock
//
// Plasticity Law: Continuum von Mises Yield Mechanics:
//   f = |sigma| - Y <= 0
//   dot{lambda} >= 0, dot{lambda} * f = 0
// =============================================================================

`timescale 1ns / 1ps

module arcloom_octal_column #(
    parameter integer CLK_FREQ_HZ     = 125_000_000,
    parameter integer YIELD_THRESHOLD = 40,          // Plastic yield stress Y
    parameter integer HARDENING_RATE  = 1,           // Strain hardening eta
    parameter integer DECAY_RATE      = 1            // Sleep pruning lambda
)(
    input  wire        clk,                          // 125 MHz system clock (H16)
    input  wire        rst_n,                        // Active-low synchronous reset (BTN0 / D19)
    input  wire        sample_tick,                  // Causal beat strobe (e.g., 20 Hz - 100 Hz)
    input  wire        sleep_mode,                   // 1 = Nocturnal consolidation & pruning
    
    // Top-Down L1 Apical Somatic Bias (From UF Kernel)
    // Encoded as 8 balanced ternary trits: {S_UF, B_k, P_k, C_k, U*, R_rev, M_k, D_k}
    input  wire [15:0] l1_somatic_dsf_trits,
    
    // Afferent Sensory Inputs (L4 Transduction)
    input  wire [7:0]  sensor_optical_focal,         // V1: Foveal optical intensity
    input  wire [7:0]  sensor_optical_motion,        // V2: Optical edge / motion gradient
    input  wire [7:0]  sensor_cochlear_formant,      // A1: Primary acoustic formant band
    input  wire [7:0]  sensor_cochlear_envelope,     // A2: Speech envelope energy
    input  wire [7:0]  sensor_palmar_contact,        // S1: Palmar tactile contact
    input  wire [7:0]  sensor_barrier_force,         // S2: Mechanical barrier resistance
    
    // Physical Scope Outputs (Pmod A Header Pins -> Siglent SDS1104X-E)
    // Sigma-Delta / PDM 1-bit high-frequency analog voltage reconstruction (0 to 3.3V)
    output wire        scope_ch1_a1_cochlear,        // Pmod A Pin 1 [Y18] - Ch1 (Yellow)
    output wire        scope_ch2_v1_optical,         // Pmod A Pin 2 [Y19] - Ch2 (Cyan)
    output wire        scope_ch3_s2_yield_stress,    // Pmod A Pin 3 [Y16] - Ch3 (Magenta)
    output wire        scope_ch4_m1_vocal_efferent,  // Pmod A Pin 4 [Y17] - Ch4 (Blue)
    
    // Diagnostic Board Outputs (LEDs LD0 - LD3)
    output reg         led_vocal_discharge,          // LD0 [R14]: Airway vocal valve fired ('say')
    output reg         led_barrier_refusal,          // LD1 [P14]: Barrier stress exceeded yield
    output reg         led_spatial_locked,           // LD2 [N16]: Recurrent spatial well persistent
    output reg         led_somatic_strained,         // LD3 [M14]: P_k > B_k (S_UF <= 0)
    
    // Digital Telemetry Registers (Bus Readout)
    output reg  [7:0]  active_synapse_count_div16,   // Scaled active modular conductances
    output reg  [7:0]  spatial_well_radius,          // Layer 5 persistent distance
    output reg  [7:0]  spatial_well_angle,           // Layer 5 persistent polar heading
    output reg  [7:0]  airway_vocal_drive            // M1 efferent acoustic drive
);

    // =========================================================================
    // 1. Column State Arrays & Interconnects
    // =========================================================================
    // Conductance matrix between adjacent columns (Horizontal Fasciculi L2/3)
    // g[i][j]: 8-bit signed conductance (-128 to +127)
    reg signed [7:0] fasciculi_conductance [0:7][0:7];
    
    // Column internal potential states (L4 afferent, L5 efferent)
    reg [7:0] col_l4_state [0:7];
    reg [7:0] col_l5_state [0:7];
    
    // Structural Field L1 Invariant Unpacking
    wire [1:0] trit_S_UF  = l1_somatic_dsf_trits[15:14];
    wire [1:0] trit_B_k   = l1_somatic_dsf_trits[13:12];
    wire [1:0] trit_P_k   = l1_somatic_dsf_trits[11:10];
    wire [1:0] trit_C_k   = l1_somatic_dsf_trits[9:8];
    wire [1:0] trit_U_st  = l1_somatic_dsf_trits[7:6];
    wire [1:0] trit_R_rev = l1_somatic_dsf_trits[5:4];
    wire [1:0] trit_M_k   = l1_somatic_dsf_trits[3:2];
    wire [1:0] trit_D_k   = l1_somatic_dsf_trits[1:0];

    // Somatic Strain Flag: S_UF <= 0 or P_k > B_k
    wire is_strained = (trit_S_UF == 2'b10) || (trit_S_UF == 2'b00) || (trit_P_k == 2'b01 && trit_B_k != 2'b01);
    
    // =========================================================================
    // 2. Optical Spatial Well & Persistence (Col 0 & Col 1)
    // =========================================================================
    // L5 Recurrent Attractor: Holds (r, theta) across occlusion
    reg [7:0] recurrent_optical_well;
    reg [7:0] recurrent_optical_angle;
    reg       spatial_well_active;
    
    always @(posedge clk) begin
        if (!rst_n) begin
            recurrent_optical_well  <= 8'd0;
            recurrent_optical_angle <= 8'd0;
            spatial_well_active     <= 1'b0;
        end else if (sample_tick) begin
            if (sensor_optical_focal > 8'd30) begin
                // Target is directly in view: update potential well
                recurrent_optical_well  <= sensor_optical_focal;
                recurrent_optical_angle <= sensor_optical_motion;
                spatial_well_active     <= 1'b1;
            end else if (spatial_well_active) begin
                // Occlusion: Recurrent self-excitation maintains potential well (slow decay)
                if (recurrent_optical_well > 8'd2)
                    recurrent_optical_well <= recurrent_optical_well - 8'd1;
                else
                    spatial_well_active <= 1'b0;
            end
        end
    end

    // =========================================================================
    // 3. Continuum Yield Stress Plasticity (Col 5 - S2 Barrier Stress)
    // =========================================================================
    reg [7:0] yield_stress_magnitude;
    reg       barrier_refusal_latch;
    
    always @(posedge clk) begin
        if (!rst_n) begin
            yield_stress_magnitude <= 8'd0;
            barrier_refusal_latch  <= 1'b0;
        end else if (sample_tick) begin
            // Continuum von Mises yield evaluation: f = |sigma| - Y
            if (sensor_barrier_force > YIELD_THRESHOLD[7:0]) begin
                yield_stress_magnitude <= sensor_barrier_force - YIELD_THRESHOLD[7:0];
                barrier_refusal_latch  <= 1'b1;
            end else begin
                yield_stress_magnitude <= 8'd0;
                barrier_refusal_latch  <= 1'b0;
            end
        end
    end

    // =========================================================================
    // 4. Motor Efferent Discharge & Vocal Valve (Col 6 - M1 & Col 7 - M2)
    // =========================================================================
    reg [7:0] airway_vocal_efferent;
    reg [7:0] motor_locomotion_stride;
    
    always @(posedge clk) begin
        if (!rst_n) begin
            airway_vocal_efferent   <= 8'd0;
            motor_locomotion_stride <= 8'd0;
        end else if (sample_tick) begin
            if (sleep_mode) begin
                airway_vocal_efferent   <= 8'd0;
                motor_locomotion_stride <= 8'd0;
            end else begin
                // Homeostatic Exhaust Coupling:
                // When strained or barrier refused without food, discharge through vocal valve
                if (is_strained || barrier_refusal_latch) begin
                    // Discharge airway vocal valve ('say' resonant syllable)
                    airway_vocal_efferent   <= 8'd220; // High amplitude vocal pulse
                    motor_locomotion_stride <= 8'd0;   // Inhibit futile pushing against barrier
                end else if (sensor_cochlear_formant > 8'd50) begin
                    // Auditory-vocal resonance response
                    airway_vocal_efferent   <= sensor_cochlear_formant;
                    motor_locomotion_stride <= 8'd30;
                end else begin
                    airway_vocal_efferent   <= 8'd0;
                    motor_locomotion_stride <= 8'd60; // Free nominal locomotion
                end
            end
        end
    end

    // =========================================================================
    // 5. Inter-Column Fasciculi Plasticity (L2/3 Yield Deformation)
    // =========================================================================
    integer c_src, c_dst;
    reg [15:0] total_active_synapses;
    
    always @(posedge clk) begin
        if (!rst_n) begin
            for (c_src = 0; c_src < 8; c_src = c_src + 1) begin
                for (c_dst = 0; c_dst < 8; c_dst = c_dst + 1) begin
                    fasciculi_conductance[c_src][c_dst] <= 8'sd0;
                end
            end
            total_active_synapses <= 16'd0;
        end else if (sample_tick) begin
            if (sleep_mode) begin
                // Nocturnal Dream Consolidation: prune weak conductances (|g| * (1 - lambda))
                for (c_src = 0; c_src < 8; c_src = c_src + 1) begin
                    for (c_dst = 0; c_dst < 8; c_dst = c_dst + 1) begin
                        if (fasciculi_conductance[c_src][c_dst] > 8'sd2)
                            fasciculi_conductance[c_src][c_dst] <= fasciculi_conductance[c_src][c_dst] - DECAY_RATE[7:0];
                        else if (fasciculi_conductance[c_src][c_dst] < -8'sd2)
                            fasciculi_conductance[c_src][c_dst] <= fasciculi_conductance[c_src][c_dst] + DECAY_RATE[7:0];
                        else
                            fasciculi_conductance[c_src][c_dst] <= 8'sd0;
                    end
                end
            end else begin
                // Plastic yield update between co-active columns: delta_g = sign(sigma) * eta * (|sigma| - Y)
                if (sensor_optical_focal > 8'd50 && sensor_cochlear_formant > 8'd50) begin
                    // Bind optical target to auditory formant (e.g. "cup" disc + acoustic sound)
                    if (fasciculi_conductance[0][2] < 8'sd120)
                        fasciculi_conductance[0][2] <= fasciculi_conductance[0][2] + HARDENING_RATE[7:0];
                end
                if (barrier_refusal_latch && airway_vocal_efferent > 8'd100) begin
                    // Bind barrier contact stress to vocal exhaust
                    if (fasciculi_conductance[5][6] < 8'sd120)
                        fasciculi_conductance[5][6] <= fasciculi_conductance[5][6] + HARDENING_RATE[7:0];
                end
            end
            
            // Tally active yielded synapses (|g| >= 4)
            total_active_synapses <= (fasciculi_conductance[0][2] > 8'sd4 ? 16'd1 : 16'd0) +
                                     (fasciculi_conductance[5][6] > 8'sd4 ? 16'd1 : 16'd0) +
                                     16'd128; // Baseline columnar minicolumn junctions
        end
    end

    // =========================================================================
    // 6. Registered Telemetry & Diagnostic LEDs
    // =========================================================================
    always @(posedge clk) begin
        if (!rst_n) begin
            led_vocal_discharge        <= 1'b0;
            led_barrier_refusal        <= 1'b0;
            led_spatial_locked         <= 1'b0;
            led_somatic_strained       <= 1'b0;
            active_synapse_count_div16 <= 8'd0;
            spatial_well_radius        <= 8'd0;
            spatial_well_angle         <= 8'd0;
            airway_vocal_drive         <= 8'd0;
        end else begin
            led_vocal_discharge        <= (airway_vocal_efferent > 8'd50);
            led_barrier_refusal        <= barrier_refusal_latch;
            led_spatial_locked         <= spatial_well_active;
            led_somatic_strained       <= is_strained;
            active_synapse_count_div16 <= total_active_synapses[11:4];
            spatial_well_radius        <= recurrent_optical_well;
            spatial_well_angle         <= recurrent_optical_angle;
            airway_vocal_drive         <= airway_vocal_efferent;
        end
    end

    // =========================================================================
    // 7. First-Order Sigma-Delta PDM DACs (Direct Analog Oscilloscope Pins)
    // =========================================================================
    // High-frequency 125 MHz 8-bit sigma-delta modulation reconstructs a continuous
    // analog voltage (0V - 3.3V) on the Pmod pins, readable directly by Siglent BNC probes.

    // Ch 1: A1 Cochlear Acoustic Formant Resonance (Pmod A1 - Y18)
    reg [8:0] dac_acc_ch1;
    always @(posedge clk) begin
        if (!rst_n) dac_acc_ch1 <= 9'd0;
        else dac_acc_ch1 <= dac_acc_ch1[7:0] + sensor_cochlear_formant;
    end
    assign scope_ch1_a1_cochlear = dac_acc_ch1[8];

    // Ch 2: V1 Optical Focal Target / Recurrent Spatial Well (Pmod A2 - Y19)
    reg [8:0] dac_acc_ch2;
    wire [7:0] ch2_signal = spatial_well_active ? recurrent_optical_well : sensor_optical_focal;
    always @(posedge clk) begin
        if (!rst_n) dac_acc_ch2 <= 9'd0;
        else dac_acc_ch2 <= dac_acc_ch2[7:0] + ch2_signal;
    end
    assign scope_ch2_v1_optical = dac_acc_ch2[8];

    // Ch 3: S2 Contact Barrier Yield Stress (|sigma| - Y) (Pmod A3 - Y16)
    reg [8:0] dac_acc_ch3;
    always @(posedge clk) begin
        if (!rst_n) dac_acc_ch3 <= 9'd0;
        else dac_acc_ch3 <= dac_acc_ch3[7:0] + yield_stress_magnitude;
    end
    assign scope_ch3_s2_yield_stress = dac_acc_ch3[8];

    // Ch 4: M1 Airway Vocal Pressure Release Pulse (Pmod A4 - Y17)
    reg [8:0] dac_acc_ch4;
    always @(posedge clk) begin
        if (!rst_n) dac_acc_ch4 <= 9'd0;
        else dac_acc_ch4 <= dac_acc_ch4[7:0] + airway_vocal_efferent;
    end
    assign scope_ch4_m1_vocal_efferent = dac_acc_ch4[8];

endmodule
