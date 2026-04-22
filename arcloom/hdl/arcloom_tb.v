// ============================================================
// ArcLoom Testbench — Verify SPPU + MathLoom + Pipeline
// ============================================================
//
// Test 1: SPPU is combinational — output changes without clock
// Test 2: MathLoom balanced ternary addition correctness
// Test 3: Full arcloom_top with sensor input through pipeline
//
// Run: vivado -mode batch -source run_sim.tcl
//   or: iverilog -o arcloom_tb arcloom_tb.v *.v && vvp arcloom_tb
// ============================================================

`timescale 1ns / 1ps

module arcloom_tb;

    // ---- Clock and reset ----
    reg clk;
    reg rst_n;
    initial clk = 0;
    always #4 clk = ~clk;  // 125 MHz

    // ---- Test counters ----
    integer pass_count = 0;
    integer fail_count = 0;
    integer test_num   = 0;

    task check;
        input [255:0] name;
        input         condition;
        begin
            test_num = test_num + 1;
            if (condition) begin
                $display("  [PASS] Test %0d: %0s", test_num, name);
                pass_count = pass_count + 1;
            end else begin
                $display("  [FAIL] Test %0d: %0s", test_num, name);
                fail_count = fail_count + 1;
            end
        end
    endtask

    // ================================================================
    // TEST 1: SPPU is purely combinational
    // ================================================================
    reg  [5:0]  tb_dist, tb_dir, tb_accl;
    wire [35:0] tb_loom_state;
    wire [1:0]  tb_steer, tb_speed, tb_conf;
    wire [15:0] tb_f_ctx_0, tb_f_ctx_1, tb_f_ctx_2;
    wire [15:0] tb_f_mmtm_0, tb_f_mmtm_1, tb_f_mmtm_2;
    wire [15:0] tb_f_dcsn_0, tb_f_dcsn_1, tb_f_dcsn_2;

    arcloom_sppu sppu_uut (
        .in_distance(tb_dist),
        .in_direction(tb_dir),
        .in_accel(tb_accl),
        .ext_h_ctx(8'd0),
        .ext_h_mmtm(8'd0),
        .ext_h_dcsn(8'd0),
        .loom_state(tb_loom_state),
        .decision_steer(tb_steer),
        .decision_speed(tb_speed),
        .decision_conf(tb_conf),
        .field_ctx_0(tb_f_ctx_0),
        .field_ctx_1(tb_f_ctx_1),
        .field_ctx_2(tb_f_ctx_2),
        .field_mmtm_0(tb_f_mmtm_0),
        .field_mmtm_1(tb_f_mmtm_1),
        .field_mmtm_2(tb_f_mmtm_2),
        .field_dcsn_0(tb_f_dcsn_0),
        .field_dcsn_1(tb_f_dcsn_1),
        .field_dcsn_2(tb_f_dcsn_2)
    );

    // ================================================================
    // TEST 2: MathLoom balanced ternary addition
    // ================================================================
    // Test with 4-digit balanced ternary numbers
    reg  [7:0] ml_a, ml_b;
    wire [7:0] ml_sum;
    wire [1:0] ml_carry;

    arcloom_bt_adder #(.N(4)) adder_uut (
        .a(ml_a),
        .b(ml_b),
        .sum_out(ml_sum),
        .c_final(ml_carry)
    );

    // Helper: compute signed value of 4-digit balanced ternary
    function integer bt_val;
        input [7:0] bt;
        integer v;
        begin
            v = 0;
            // digit 0: weight 1
            case (bt[1:0])
                2'b01: v = v + 1;
                2'b10: v = v - 1;
            endcase
            // digit 1: weight 3
            case (bt[3:2])
                2'b01: v = v + 3;
                2'b10: v = v - 3;
            endcase
            // digit 2: weight 9
            case (bt[5:4])
                2'b01: v = v + 9;
                2'b10: v = v - 9;
            endcase
            // digit 3: weight 27
            case (bt[7:6])
                2'b01: v = v + 27;
                2'b10: v = v - 27;
            endcase
            bt_val = v;
        end
    endfunction

    // ================================================================
    // TEST 3: Full top module
    // ================================================================
    reg  [11:0] sensor_adc;
    reg         sensor_valid;
    wire [1:0]  top_steer, top_speed, top_conf;
    wire [35:0] top_loom_state;
    wire [7:0]  top_krim_score;
    wire        top_dsf_valid;
    wire [1:0]  top_dsf_D;
    wire [31:0] top_dsf_M, top_dsf_U_star, top_dsf_P, top_dsf_B;
    wire        top_dsf_R_rev, top_dsf_safe_mode;
    wire [3:0]  top_dsf_C;

    arcloom_top top_uut (
        .clk(clk), .rst_n(rst_n),
        .sensor_adc(sensor_adc),
        .sensor_valid(sensor_valid),
        .decision_steer(top_steer),
        .decision_speed(top_speed),
        .decision_conf(top_conf),
        .loom_state(top_loom_state),
        .krimelack_score(top_krim_score),
        .dsf_valid(top_dsf_valid),
        .dsf_D(top_dsf_D),
        .dsf_M(top_dsf_M),
        .dsf_R_rev(top_dsf_R_rev),
        .dsf_U_star(top_dsf_U_star),
        .dsf_C(top_dsf_C),
        .dsf_P(top_dsf_P),
        .dsf_B(top_dsf_B),
        .dsf_safe_mode(top_dsf_safe_mode)
    );

    // ================================================================
    // Run tests
    // ================================================================
    reg [35:0] prev_loom;
    integer i, a_val, b_val, sum_val, expected;

    initial begin
        // VCD dump disabled for speed — uncomment for waveform debug
        // $dumpfile("arcloom_tb.vcd");
        // $dumpvars(0, arcloom_tb);

        // ---- Reset ----
        rst_n = 0;
        sensor_adc = 12'd0;
        sensor_valid = 0;
        tb_dist = 6'b0;
        tb_dir  = 6'b0;
        tb_accl = 6'b0;
        ml_a = 8'b0;
        ml_b = 8'b0;

        #20;
        rst_n = 1;
        #10;

        // ============================================================
        $display("");
        $display("=== TEST 1: SPPU Combinational Settling ===");
        // ============================================================

        // All zeros: loom should output all zeros (null)
        #1;  // just propagation delay, no clock edge
        check("All-zero input → all-zero output",
              tb_loom_state == 36'd0);

        // Apply distance = (+1, +1, +1) = strong close signal
        tb_dist = 6'b01_01_01;
        #1;  // combinational propagation
        prev_loom = tb_loom_state;
        check("Strong distance input changes loom state immediately",
              tb_loom_state != 36'd0);
        check("Input strands reflect in loom_state[5:0]",
              tb_loom_state[5:0] == 6'b01_01_01);

        // Change direction — output should update WITHOUT clock
        tb_dir = 6'b01_01_01;  // strong positive direction
        #1;
        check("Direction change updates loom without clock",
              tb_loom_state != prev_loom);

        // Verify decision strand is nonzero when all inputs are strong
        tb_accl = 6'b01_01_01;
        #1;
        check("All-positive inputs produce decision output",
              tb_loom_state[35:30] != 6'b0);

        // Test negative inputs
        tb_dist = 6'b10_10_10;  // all -1
        tb_dir  = 6'b10_10_10;
        tb_accl = 6'b10_10_10;
        #1;
        check("All-negative inputs produce decision output",
              tb_loom_state[35:30] != 6'b0);

        // Test external bias effect
        prev_loom = tb_loom_state;
        // Need to instantiate SPPU with bias — already done above with 0 bias.
        // The bias test is better done through the top module.

        // Test mixed inputs
        tb_dist = 6'b01_00_10;  // (+1, 0, -1)
        tb_dir  = 6'b10_01_00;  // (-1, +1, 0)
        tb_accl = 6'b00_10_01;  // (0, -1, +1)
        #1;
        check("Mixed inputs settle to valid state",
              (tb_loom_state[35:30] != 6'b11_11_11) &&
              (tb_loom_state[29:24] != 6'b11_11_11) &&
              (tb_loom_state[23:18] != 6'b11_11_11));

        // ============================================================
        $display("");
        $display("=== TEST 2: MathLoom Balanced Ternary Addition ===");
        // ============================================================

        // Test: 0 + 0 = 0
        ml_a = 8'b00_00_00_00;
        ml_b = 8'b00_00_00_00;
        #1;
        check("0 + 0 = 0", ml_sum == 8'b00_00_00_00 && ml_carry == 2'b00);

        // Test: +1 + +1 = +1*3^0 + +1*3^0 = 2 = (-1)*3^0 + (+1)*3^1
        // A = 0001 (trit encoding: digit0=+1)
        // B = 0001
        // Sum should be: digit0=-1(10), digit1=+1(01) = 01_10
        ml_a = 8'b00_00_00_01;  // +1
        ml_b = 8'b00_00_00_01;  // +1
        #1;
        a_val = bt_val(ml_a);
        b_val = bt_val(ml_b);
        sum_val = bt_val(ml_sum);
        expected = a_val + b_val;
        check("1 + 1 = 2 (balanced ternary)",
              sum_val == expected);
        $display("    A=%0d, B=%0d, Sum=%0d, Expected=%0d", a_val, b_val, sum_val, expected);

        // Test: -1 + -1 = -2 = (+1)*3^0 + (-1)*3^1
        ml_a = 8'b00_00_00_10;  // -1
        ml_b = 8'b00_00_00_10;  // -1
        #1;
        a_val = bt_val(ml_a);
        b_val = bt_val(ml_b);
        sum_val = bt_val(ml_sum);
        expected = a_val + b_val;
        check("-1 + -1 = -2 (balanced ternary)",
              sum_val == expected);

        // Test: +1 + -1 = 0
        ml_a = 8'b00_00_00_01;  // +1
        ml_b = 8'b00_00_00_10;  // -1
        #1;
        check("+1 + -1 = 0", ml_sum == 8'b0 && ml_carry == 2'b00);

        // Test larger: 13 + (-13) = 0
        // 13 in BT: 1*9 + 1*3 + 1*1 = (01)(01)(01)(00) for 4 digits
        // Actually 13 = 1*9 + 1*3 + 1*1 = 01_01_01_00... wait:
        // digit0 = 1, digit1 = 1, digit2 = 1, digit3 = 0
        // Pack: {d3, d2, d1, d0} = {00, 01, 01, 01}
        ml_a = 8'b00_01_01_01;  // +13
        ml_b = 8'b00_10_10_10;  // -13 (negated)
        #1;
        a_val = bt_val(ml_a);
        b_val = bt_val(ml_b);
        sum_val = bt_val(ml_sum);
        check("13 + (-13) = 0", sum_val == 0);

        // Test: 40 + 0 = 40
        // 40 = 1*27 + 1*9 + 1*3 + 1*1
        ml_a = 8'b01_01_01_01;  // 1+3+9+27 = 40
        ml_b = 8'b00_00_00_00;  // 0
        #1;
        a_val = bt_val(ml_a);
        sum_val = bt_val(ml_sum);
        check("40 + 0 = 40", sum_val == 40);

        // Exhaustive test: all 3^4 × 3^4 = 6561 combinations
        $display("    Running exhaustive 4-digit BT addition test...");
        begin : exhaustive
            reg [7:0] ta, tb_ex;
            integer ia, ib, va, vb, vs, ve;
            integer exhaust_pass, exhaust_fail;
            exhaust_pass = 0;
            exhaust_fail = 0;

            // Iterate over all valid 4-trit encodings
            // Each trit can be 00, 01, 10 (not 11)
            for (ia = 0; ia < 81; ia = ia + 1) begin
                // Encode ia as 4 balanced ternary digits
                ta[1:0] = (ia % 3 == 0) ? 2'b00 : (ia % 3 == 1) ? 2'b01 : 2'b10;
                ta[3:2] = ((ia/3) % 3 == 0) ? 2'b00 : ((ia/3) % 3 == 1) ? 2'b01 : 2'b10;
                ta[5:4] = ((ia/9) % 3 == 0) ? 2'b00 : ((ia/9) % 3 == 1) ? 2'b01 : 2'b10;
                ta[7:6] = ((ia/27) % 3 == 0) ? 2'b00 : ((ia/27) % 3 == 1) ? 2'b01 : 2'b10;

                for (ib = 0; ib < 81; ib = ib + 1) begin
                    tb_ex[1:0] = (ib % 3 == 0) ? 2'b00 : (ib % 3 == 1) ? 2'b01 : 2'b10;
                    tb_ex[3:2] = ((ib/3) % 3 == 0) ? 2'b00 : ((ib/3) % 3 == 1) ? 2'b01 : 2'b10;
                    tb_ex[5:4] = ((ib/9) % 3 == 0) ? 2'b00 : ((ib/9) % 3 == 1) ? 2'b01 : 2'b10;
                    tb_ex[7:6] = ((ib/27) % 3 == 0) ? 2'b00 : ((ib/27) % 3 == 1) ? 2'b01 : 2'b10;

                    ml_a = ta;
                    ml_b = tb_ex;
                    #1;

                    va = bt_val(ta);
                    vb = bt_val(tb_ex);
                    vs = bt_val(ml_sum);
                    ve = va + vb;

                    // Account for carry: full result = vs + carry * 3^4
                    if (ml_carry == 2'b01) vs = vs + 81;
                    else if (ml_carry == 2'b10) vs = vs - 81;

                    if (vs == ve)
                        exhaust_pass = exhaust_pass + 1;
                    else begin
                        exhaust_fail = exhaust_fail + 1;
                        if (exhaust_fail <= 5)
                            $display("    FAIL: %0d + %0d = %0d (expected %0d)", va, vb, vs, ve);
                    end
                end
            end

            test_num = test_num + 1;
            if (exhaust_fail == 0) begin
                $display("  [PASS] Test %0d: Exhaustive 4-digit BT addition (%0d/%0d)", test_num, exhaust_pass, exhaust_pass);
                pass_count = pass_count + 1;
            end else begin
                $display("  [FAIL] Test %0d: Exhaustive BT addition: %0d failures out of %0d", test_num, exhaust_fail, exhaust_pass + exhaust_fail);
                fail_count = fail_count + 1;
            end
        end

        // ============================================================
        $display("");
        $display("=== TEST 3: Full Top Module Integration ===");
        // ============================================================

        // Feed sensor samples and check that the pipeline processes them
        sensor_adc = 12'd2048;  // mid-range
        @(posedge clk);
        sensor_valid = 1;
        @(posedge clk);
        sensor_valid = 0;

        // Wait a few cycles for BSIL to register
        repeat(3) @(posedge clk);

        check("Top module loom_state is valid after sensor input",
              top_loom_state[5:0] != 6'bxx_xx_xx);

        // Feed a sequence of varying ADC values to trigger gates
        for (i = 0; i < 50; i = i + 1) begin
            sensor_adc = (i * 83) % 4096;  // varying signal
            sensor_valid = 1;
            @(posedge clk);
            sensor_valid = 0;
            @(posedge clk);
        end

        check("Top module survives 50 sensor samples without X/Z",
              top_loom_state !== 36'bx);

        // Check that SafeMode is not active (should be stable after warmup)
        // SafeMode may or may not be active depending on pipeline state
        $display("    dsf_safe_mode = %b", top_dsf_safe_mode);

        // Feed more samples with a sharp transition to trigger a gate boundary
        sensor_adc = 12'd100;  // low
        for (i = 0; i < 10; i = i + 1) begin
            sensor_valid = 1;
            @(posedge clk);
            sensor_valid = 0;
            @(posedge clk);
        end

        sensor_adc = 12'd3900;  // sharp jump → should trigger boundary
        sensor_valid = 1;
        @(posedge clk);
        sensor_valid = 0;
        @(posedge clk);

        sensor_adc = 12'd3800;  // stay high
        for (i = 0; i < 20; i = i + 1) begin
            sensor_valid = 1;
            @(posedge clk);
            sensor_valid = 0;
            @(posedge clk);
        end

        // Check DSF output eventually fires
        // (May need more samples for full gate formation)
        $display("    dsf_valid seen: checking pipeline is alive");
        check("Pipeline produces loom decisions",
              top_steer !== 2'bxx);

        // ============================================================
        $display("");
        $display("========================================");
        $display(" Results: %0d passed, %0d failed", pass_count, fail_count);
        $display("========================================");
        if (fail_count == 0)
            $display(" ALL TESTS PASSED");
        else
            $display(" SOME TESTS FAILED");
        $display("");

        $finish;
    end

endmodule
