// =============================================================================
// ArcLoom 8-Column Balanced Octet Testbench — Rigorous Physical Verification
// Target Substrate: Xilinx Zynq-7020 (XC7Z020-1CLG400C) @ 125 MHz
// Probing Scope: Siglent SDS1104X-E (Pmod A Pins JA1-JA4)
//
// Tests Continuum Physics & Hardware Mechanics:
//   Test 1: Synchronous Reset & Quiescent State Invariance
//   Test 2: Optical Spatial Well Attractor Persistence (V1/V2 Occlusion Hold)
//   Test 3: Acoustic-Optical Plastic Fasciculi Yielding (A1 <-> V1 Binding)
//   Test 4: von Mises Mechanical Barrier Stress & Homeostatic Vocal Exhaust (S2 -> M1)
//   Test 5: First-Order Sigma-Delta PDM DAC Duty Cycle Linearity (4-Channel Scope)
//   Test 6: Nocturnal Sleep Pruning & Conductance Preservation
// =============================================================================

`timescale 1ns / 1ps

module arcloom_octal_tb;

    // ---- System Clock & Causal Strobe ----
    reg clk;
    reg rst_n;
    reg sample_tick;
    reg sleep_mode;

    // 125 MHz clock (8.000 ns period -> 4.000 ns half-period)
    initial clk = 1'b0;
    always #4 clk = ~clk;

    // ---- Top-Down Somatic Bias Trits ----
    // {S_UF, B_k, P_k, C_k, U*, R_rev, M_k, D_k}
    reg [15:0] l1_somatic_dsf_trits;

    // ---- Afferent Sensory Transduction ----
    reg [7:0] sensor_optical_focal;
    reg [7:0] sensor_optical_motion;
    reg [7:0] sensor_cochlear_formant;
    reg [7:0] sensor_cochlear_envelope;
    reg [7:0] sensor_palmar_contact;
    reg [7:0] sensor_barrier_force;

    // ---- Oscilloscope Probing Outputs (Pmod A JA1-JA4) ----
    wire scope_ch1_a1_cochlear;
    wire scope_ch2_v1_optical;
    wire scope_ch3_s2_yield_stress;
    wire scope_ch4_m1_vocal_efferent;

    // ---- Board Diagnostic LEDs ----
    wire led_vocal_discharge;
    wire led_barrier_refusal;
    wire led_spatial_locked;
    wire led_somatic_strained;

    // ---- Digital Telemetry Readouts ----
    wire [7:0] active_synapse_count_div16;
    wire [7:0] spatial_well_radius;
    wire [7:0] spatial_well_angle;
    wire [7:0] airway_vocal_drive;

    // ---- DUT Instantiation ----
    arcloom_octal_column #(
        .CLK_FREQ_HZ(125_000_000),
        .YIELD_THRESHOLD(40),
        .HARDENING_RATE(2),
        .DECAY_RATE(1)
    ) dut (
        .clk(clk),
        .rst_n(rst_n),
        .sample_tick(sample_tick),
        .sleep_mode(sleep_mode),
        .l1_somatic_dsf_trits(l1_somatic_dsf_trits),
        .sensor_optical_focal(sensor_optical_focal),
        .sensor_optical_motion(sensor_optical_motion),
        .sensor_cochlear_formant(sensor_cochlear_formant),
        .sensor_cochlear_envelope(sensor_cochlear_envelope),
        .sensor_palmar_contact(sensor_palmar_contact),
        .sensor_barrier_force(sensor_barrier_force),
        .scope_ch1_a1_cochlear(scope_ch1_a1_cochlear),
        .scope_ch2_v1_optical(scope_ch2_v1_optical),
        .scope_ch3_s2_yield_stress(scope_ch3_s2_yield_stress),
        .scope_ch4_m1_vocal_efferent(scope_ch4_m1_vocal_efferent),
        .led_vocal_discharge(led_vocal_discharge),
        .led_barrier_refusal(led_barrier_refusal),
        .led_spatial_locked(led_spatial_locked),
        .led_somatic_strained(led_somatic_strained),
        .active_synapse_count_div16(active_synapse_count_div16),
        .spatial_well_radius(spatial_well_radius),
        .spatial_well_angle(spatial_well_angle),
        .airway_vocal_drive(airway_vocal_drive)
    );

    // ---- Test Tracking ----
    integer pass_count = 0;
    integer fail_count = 0;

    // Helper task: generate N sample ticks
    task strobe_sample_ticks;
        input integer count;
        integer i;
        begin
            for (i = 0; i < count; i = i + 1) begin
                @(posedge clk);
                sample_tick = 1'b1;
                @(posedge clk);
                sample_tick = 1'b0;
                repeat (3) @(posedge clk);
            end
        end
    endtask

    // PDM pulse counting helper
    integer pdm_cycles;
    integer ch1_pulses;
    integer ch2_pulses;
    integer ch3_pulses;
    integer ch4_pulses;

    task count_pdm_pulses;
        input integer cycles;
        integer k;
        begin
            ch1_pulses = 0;
            ch2_pulses = 0;
            ch3_pulses = 0;
            ch4_pulses = 0;
            for (k = 0; k < cycles; k = k + 1) begin
                @(posedge clk);
                if (scope_ch1_a1_cochlear) ch1_pulses = ch1_pulses + 1;
                if (scope_ch2_v1_optical)  ch2_pulses = ch2_pulses + 1;
                if (scope_ch3_s2_yield_stress) ch3_pulses = ch3_pulses + 1;
                if (scope_ch4_m1_vocal_efferent) ch4_pulses = ch4_pulses + 1;
            end
        end
    endtask

    // =========================================================================
    // Simulation Flow
    // =========================================================================
    initial begin
        $dumpfile("arcloom_octal_tb.vcd");
        $dumpvars(0, arcloom_octal_tb);

        $display("\n============================================================");
        $display("ARCLOOM 8-COLUMN BALANCED OCTET TESTBENCH");
        $display("Continuum Plasticity & 4-Channel Oscilloscope Simulation");
        $display("============================================================\n");

        // Initialize signals
        rst_n                     = 1'b0;
        sample_tick               = 1'b0;
        sleep_mode                = 1'b0;
        l1_somatic_dsf_trits      = 16'b01_01_00_01_00_00_01_01; // S_UF=+1, B_k=+1, P_k=0, D_k=+1
        sensor_optical_focal      = 8'd0;
        sensor_optical_motion     = 8'd0;
        sensor_cochlear_formant   = 8'd0;
        sensor_cochlear_envelope  = 8'd0;
        sensor_palmar_contact     = 8'd0;
        sensor_barrier_force      = 8'd0;

        // -------------------------------------------------------------
        // TEST 1: Reset Invariance
        // -------------------------------------------------------------
        $display("[TEST 1] Verifying Synchronous Reset & Quiescent Invariance...");
        repeat (10) @(posedge clk);
        if (spatial_well_radius == 8'd0 && airway_vocal_drive == 8'd0 &&
            led_vocal_discharge == 1'b0 && led_barrier_refusal == 1'b0 &&
            led_spatial_locked == 1'b0) begin
            $display("  PASS: Quiescent state cleanly zeroed under reset.");
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: Non-zero state observed during reset!");
            fail_count = fail_count + 1;
        end

        // Release reset
        @(posedge clk);
        rst_n = 1'b1;
        repeat (5) @(posedge clk);

        // -------------------------------------------------------------
        // TEST 2: Optical Spatial Well Attractor Persistence (V1/V2)
        // -------------------------------------------------------------
        $display("\n[TEST 2] Verifying Optical Spatial Well Persistence across Occlusion...");
        // Expose foveal target (radius 180, motion angle 64)
        sensor_optical_focal  = 8'd180;
        sensor_optical_motion = 8'd64;
        strobe_sample_ticks(4);

        if (spatial_well_radius == 8'd180 && spatial_well_angle == 8'd64 && led_spatial_locked == 1'b1) begin
            $display("  PASS: Spatial well successfully locked (r=%0d, theta=%0d).",
                     spatial_well_radius, spatial_well_angle);
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: Spatial well failed to lock! r=%0d, locked=%b",
                     spatial_well_radius, led_spatial_locked);
            fail_count = fail_count + 1;
        end

        // Simulate complete visual occlusion (target vanishes: focal = 0)
        sensor_optical_focal  = 8'd0;
        sensor_optical_motion = 8'd0;
        strobe_sample_ticks(5);

        // Under occlusion, attractor well must persist with slow decay: 180 - 5 = 175 > 0
        if (spatial_well_radius >= 8'd170 && spatial_well_radius <= 8'd178 && led_spatial_locked == 1'b1) begin
            $display("  PASS: Attractor well sustained across visual occlusion (persisting r=%0d).",
                     spatial_well_radius);
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: Attractor collapsed prematurely! r=%0d, locked=%b",
                     spatial_well_radius, led_spatial_locked);
            fail_count = fail_count + 1;
        end

        // -------------------------------------------------------------
        // TEST 3: Acoustic-Optical Plastic Fasciculi Yielding (A1 <-> V1)
        // -------------------------------------------------------------
        $display("\n[TEST 3] Verifying Acoustic-Optical Plastic Yielding (A1 <-> V1 Binding)...");
        sensor_optical_focal    = 8'd200;
        sensor_cochlear_formant = 8'd160;
        
        // Strobe 10 causal ticks to drive plastic deformation
        strobe_sample_ticks(10);

        if (dut.fasciculi_conductance[0][2] == 8'sd20) begin
            $display("  PASS: Continuum yield plasticity hardened V1-A1 bridge: g[0][2]=%0d.",
                     dut.fasciculi_conductance[0][2]);
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: Plastic yield failed to harden! g[0][2]=%0d",
                     dut.fasciculi_conductance[0][2]);
            fail_count = fail_count + 1;
        end

        // Clear acoustic and optical stimuli for clean state isolation
        sensor_optical_focal    = 8'd0;
        sensor_cochlear_formant = 8'd0;
        strobe_sample_ticks(2);

        // -------------------------------------------------------------
        // TEST 4: von Mises Barrier Stress & Vocal Exhaust (S2 -> M1)
        // -------------------------------------------------------------
        $display("\n[TEST 4] Verifying von Mises Barrier Yield Stress & Vocal Discharge...");
        // 4A: Normal contact below yield (S2 = 25 <= Y=40)
        sensor_barrier_force = 8'd25;
        strobe_sample_ticks(3);

        if (led_barrier_refusal == 1'b0 && dut.motor_locomotion_stride == 8'd60 && airway_vocal_drive == 8'd0) begin
            $display("  PASS: Sub-yield barrier force (|sigma| <= Y) permits nominal locomotion (stride=60).");
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: Sub-yield barrier caused false refusal! refusal=%b, stride=%0d",
                     led_barrier_refusal, dut.motor_locomotion_stride);
            fail_count = fail_count + 1;
        end

        // 4B: Barrier impact exceeding yield (S2 = 180 > Y=40 -> f = 140 > 0)
        sensor_barrier_force = 8'd180;
        strobe_sample_ticks(3);

        if (led_barrier_refusal == 1'b1 && dut.yield_stress_magnitude == 8'd140 &&
            dut.motor_locomotion_stride == 8'd0 && airway_vocal_drive == 8'd220 &&
            led_vocal_discharge == 1'b1) begin
            $display("  PASS: Yield stress violated (f=%0d). Locomotion inhibited, vocal exhaust discharged (drive=220).",
                     dut.yield_stress_magnitude);
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: Over-yield failure mode incorrect! refusal=%b, f=%0d, stride=%0d, vocal=%0d",
                     led_barrier_refusal, dut.yield_stress_magnitude, dut.motor_locomotion_stride, airway_vocal_drive);
            fail_count = fail_count + 1;
        end

        // -------------------------------------------------------------
        // TEST 5: First-Order Sigma-Delta PDM DAC Duty Cycle Linearity
        // -------------------------------------------------------------
        $display("\n[TEST 5] Verifying 4-Channel Oscilloscope Sigma-Delta PDM Reconstruction...");
        // Assert specific test signals across all channels:
        sensor_cochlear_formant = 8'd160; // Ch1 -> 160 / 256 = 62.5% (1600 pulses / 2560)
        // Ch2 -> spatial well persistent attractor is 190 / 256 = 74.2% (1900 pulses / 2560)
        // Ch3 -> yield stress magnitude is 140 / 256 = 54.7% (1400 pulses / 2560)
        // Ch4 -> airway vocal drive is 220 / 256 = 85.9% (2200 pulses / 2560)
        count_pdm_pulses(2560); // 10 full DAC periods of 256 ticks

        $display("  Measured PDM Pulse Densities across 2560 clock cycles:");
        $display("    Ch1 (A1 Acoustic):   %0d / 2560 (%0.1f%%) [Ideal: 62.5%%]",
                 ch1_pulses, (ch1_pulses * 100.0) / 2560.0);
        $display("    Ch2 (V1 Spatial):    %0d / 2560 (%0.1f%%) [Ideal: 74.2%%]",
                 ch2_pulses, (ch2_pulses * 100.0) / 2560.0);
        $display("    Ch3 (S2 Stress):     %0d / 2560 (%0.1f%%) [Ideal: 54.7%%]",
                 ch3_pulses, (ch3_pulses * 100.0) / 2560.0);
        $display("    Ch4 (M1 Vocal DAC):  %0d / 2560 (%0.1f%%) [Ideal: 85.9%%]",
                 ch4_pulses, (ch4_pulses * 100.0) / 2560.0);

        if (ch1_pulses >= 1550 && ch1_pulses <= 1650 &&
            ch2_pulses >= 1850 && ch2_pulses <= 1950 &&
            ch3_pulses >= 1350 && ch3_pulses <= 1450 &&
            ch4_pulses >= 2150 && ch4_pulses <= 2250) begin
            $display("  PASS: All 4 Siglent oscilloscope probe channels demonstrate linear PDM reconstruction.");
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: PDM pulse density outside linear tolerance bounds!");
            fail_count = fail_count + 1;
        end

        // -------------------------------------------------------------
        // TEST 6: Nocturnal Sleep Pruning & Consolidation
        // -------------------------------------------------------------
        $display("\n[TEST 6] Verifying Nocturnal Dream Consolidation & Synaptic Pruning...");
        // Enter nocturnal sleep: eyes closed, silent, quiescent
        sensor_barrier_force    = 8'd0;
        sensor_cochlear_formant = 8'd0;
        sensor_optical_focal    = 8'd0;
        sleep_mode              = 1'b1;
        
        // Measure initial conductance before sleep
        $display("  Pre-sleep conductance g[0][2] = %0d", dut.fasciculi_conductance[0][2]);
        
        // Strobe 6 sleep consolidation ticks (decay rate = 1 per tick)
        strobe_sample_ticks(6);

        $display("  Post-sleep conductance g[0][2] = %0d (decayed by 6)", dut.fasciculi_conductance[0][2]);

        if (dut.fasciculi_conductance[0][2] == 8'sd14 &&
            dut.airway_vocal_efferent == 8'd0 && dut.motor_locomotion_stride == 8'd0) begin
            $display("  PASS: Nocturnal pruning precisely decayed synaptic conductance (20 -> 14) with total motor quiescence.");
            pass_count = pass_count + 1;
        end else begin
            $display("  FAIL: Sleep pruning failed! g[0][2]=%0d, vocal=%0d, stride=%0d",
                     dut.fasciculi_conductance[0][2], dut.airway_vocal_efferent, dut.motor_locomotion_stride);
            fail_count = fail_count + 1;
        end

        // =============================================================
        // Final Summary
        // =============================================================
        $display("\n============================================================");
        $display("TESTBENCH COMPLETE: %0d PASSED, %0d FAILED", pass_count, fail_count);
        $display("============================================================\n");

        if (fail_count == 0) begin
            $display(">>> ALL ARCLOOM CONTINUUM MECHANICS & PDM DAC CHECKS PASSED <<<\n");
            $finish(0);
        end else begin
            $display(">>> TESTBENCH FAILED: ENCOUNTERED INVARIANT VIOLATIONS <<<\n");
            $finish(1);
        end
    end

endmodule
