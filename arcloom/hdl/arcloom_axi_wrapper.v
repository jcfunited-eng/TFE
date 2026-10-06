// ============================================================
// ArcLoom AXI Wrapper — PYNQ Zynq-7000 Memory Map (Camera-Free)
// ============================================================
//
// Pure Physical Hardware Substrate Interface
//
// AXI4-Lite slave interface to ArcLoom ternary neuromorphic core
// and MathLoom 12-trit balanced ternary arithmetic unit.
//
// Address map (word-addressed via S_AXI_AWADDR[7:2]):
//   0x00: Decision + Status [31:0]
//   0x04: Loom state [31:0] (Decision [5:0], Context [11:6], Momentum [17:12])
//   0x08: MathLoom ADD (12-trit) + Comparison [31:0]
//   0x0C: MathLoom MUL (low) or DIV quotient [31:0]
//   0x10: MathLoom DIV remainder + cycle count [31:0]
//         Write: motor enable [2], Krimelack commit [1]
//   0x14: MathLoom MUL product high [31:0]
//         Write: familiarity override [7:0], enable [8]
//   0x1C: Left/Right sensor raw ADC [31:0]
//   0x20: Krimelack status + target match [31:0]
//   0x28: Front sensor raw ADC + motor_enable status [31:0]
//   0x30: Hardware distance baselines: Front [11:0], Left [27:16]
//   0x34: Hardware distance baseline: Right [11:0]
//   0x40-0x54: Full 81-trit loom_state (6 registers, 162 bits)
//   0x74: Division cycle count [18:0]
//   0x78: MathLoom ABI identifier (0x4D4C0001)
//   0x7C: Division status {div_pending[2], div_dbz[1], div_ready[0]}
// ============================================================

module arcloom_axi_wrapper #(
    parameter C_S_AXI_DATA_WIDTH = 32,
    parameter C_S_AXI_ADDR_WIDTH = 8
)(
    input  wire                                S_AXI_ACLK,
    input  wire                                S_AXI_ARESETN,
    input  wire [C_S_AXI_ADDR_WIDTH-1:0]       S_AXI_AWADDR,
    input  wire [2:0]                          S_AXI_AWPROT,
    input  wire                                S_AXI_AWVALID,
    output wire                                S_AXI_AWREADY,
    input  wire [C_S_AXI_DATA_WIDTH-1:0]       S_AXI_WDATA,
    input  wire [C_S_AXI_DATA_WIDTH/8-1:0]     S_AXI_WSTRB,
    input  wire                                S_AXI_WVALID,
    output wire                                S_AXI_WREADY,
    output wire [1:0]                          S_AXI_BRESP,
    output wire                                S_AXI_BVALID,
    input  wire                                S_AXI_BREADY,
    input  wire [C_S_AXI_ADDR_WIDTH-1:0]       S_AXI_ARADDR,
    input  wire [2:0]                          S_AXI_ARPROT,
    input  wire                                S_AXI_ARVALID,
    output wire                                S_AXI_ARREADY,
    output wire [C_S_AXI_DATA_WIDTH-1:0]       S_AXI_RDATA,
    output wire [1:0]                          S_AXI_RRESP,
    output wire                                S_AXI_RVALID,
    input  wire                                S_AXI_RREADY,

    // 3 sensor inputs from XADC
    input  wire [15:0]                         hw_sensor_data,
    input  wire                                hw_sensor_valid,
    input  wire [15:0]                         hw_sensor_data_left,
    input  wire                                hw_sensor_valid_left,
    input  wire [15:0]                         hw_sensor_data_right,
    input  wire                                hw_sensor_valid_right,

    // Motor drive outputs (Pmod A)
    output wire                                motor_ain1,
    output wire                                motor_ain2,
    output wire                                motor_bin1,
    output wire                                motor_bin2
);

    reg axi_bvalid, axi_rvalid, axi_write_error;
    reg aw_pending, w_pending;
    reg [C_S_AXI_ADDR_WIDTH-1:0] axi_awaddr;
    reg [31:0] axi_wdata;
    reg [3:0] axi_wstrb;
    reg [C_S_AXI_DATA_WIDTH-1:0] axi_rdata;

    assign S_AXI_AWREADY = !aw_pending && !axi_bvalid;
    assign S_AXI_WREADY  = !w_pending && !axi_bvalid;
    assign S_AXI_BRESP   = axi_write_error ? 2'b10 : 2'b00;
    assign S_AXI_BVALID  = axi_bvalid;
    assign S_AXI_ARREADY = !axi_rvalid;
    assign S_AXI_RDATA   = axi_rdata;
    assign S_AXI_RRESP   = 2'b00;
    assign S_AXI_RVALID  = axi_rvalid;

    // ---- Write registers ----
    reg [11:0] sw_sensor_adc;
    reg [2:0]  sw_valid_stretch;
    reg        motor_enable;
    reg        sw_krim_commit;
    reg [7:0]  sw_familiarity;
    reg        sw_fam_enable;
    reg [23:0] mathloom_a, mathloom_b;

    // Hardware distance baselines (0 = use hardware parameter default)
    reg [11:0] sensor_bl_front;
    reg [11:0] sensor_bl_left;
    reg [11:0] sensor_bl_right;

    // ---- Latched MathLoom results (12-trit) ----
    reg [23:0] ml_sum_r;
    reg [1:0]  ml_carry_r;
    reg [47:0] ml_product_r;
    reg        ml_eq_r, ml_gt_r, ml_lt_r;

    // ---- Latched left/right sensor data ----
    reg [11:0] left_adc_r, right_adc_r;

    // ---- Front sensor ADC latch for debug register ----
    wire [11:0] hw_adc = hw_sensor_data[15:4];
    reg [11:0] live_adc;
    always @(posedge S_AXI_ACLK)
        if (hw_sensor_valid) live_adc <= hw_adc;

    // Latch left/right sensor values
    always @(posedge S_AXI_ACLK) begin
        if (hw_sensor_valid_left)  left_adc_r  <= hw_sensor_data_left[15:4];
        if (hw_sensor_valid_right) right_adc_r <= hw_sensor_data_right[15:4];
    end

    // ---- Sensor data multiplexer (sw override vs hw) ----
    wire [11:0] sensor_adc_in = (sw_valid_stretch != 0) ? sw_sensor_adc : hw_adc;
    wire sensor_valid_in = (sw_valid_stretch != 0) || hw_sensor_valid;

    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN)
            sw_valid_stretch <= 3'd0;
        else if (sw_valid_stretch != 0)
            sw_valid_stretch <= sw_valid_stretch - 3'd1;
    end

    // ---- ArcLoom Core Signals ----
    wire [1:0]  decision_steer_w, decision_speed_w, decision_conf_w;
    wire        structural_lock_w, dsf_safe_mode_w, dsf_valid_w;
    wire [1:0]  dsf_D_w;
    wire        dsf_R_rev_w;
    wire [161:0] loom_state_w;
    wire [6:0]  n_effective_w;
    wire [7:0]  omega_w;
    wire [5:0]  krim_count_w;
    wire [7:0]  krim_score_w;
    wire        krim_recall_w;
    wire        krim_commit_ok_w, krim_commit_rej_w;
    wire [7:0]  target_match_score_w;
    wire signed [31:0] debug_steer_field_w;

    // Registered outputs
    reg [1:0]  decision_steer, decision_speed, decision_conf;
    reg        structural_lock, dsf_safe_mode, dsf_valid;
    reg [1:0]  dsf_D;
    reg        dsf_R_rev;
    reg [6:0]  n_effective;
    reg [7:0]  omega;
    reg [5:0]  krim_count;
    reg [7:0]  krim_score;
    reg        krim_recall;
    reg        krim_commit_ok, krim_commit_rej;
    reg signed [31:0] debug_steer_field;

    // 81 trits = 162 bits fits in 6 32-bit registers (6 × 32 = 192 bits)
    reg [31:0] loom_state_r [0:5];

    integer i;

    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            for (i = 0; i < 6; i = i + 1)
                loom_state_r[i] <= 32'd0;
        end else begin
            loom_state_r[0] <= loom_state_w[31:0];
            loom_state_r[1] <= loom_state_w[63:32];
            loom_state_r[2] <= loom_state_w[95:64];
            loom_state_r[3] <= loom_state_w[127:96];
            loom_state_r[4] <= loom_state_w[159:128];
            loom_state_r[5] <= {30'd0, loom_state_w[161:160]};
        end
    end

    always @(posedge S_AXI_ACLK) begin
        decision_steer  <= decision_steer_w;
        decision_speed  <= decision_speed_w;
        decision_conf   <= decision_conf_w;
        structural_lock <= structural_lock_w;
        dsf_safe_mode   <= dsf_safe_mode_w;
        dsf_valid       <= dsf_valid_w;
        dsf_D           <= dsf_D_w;
        dsf_R_rev       <= dsf_R_rev_w;
        n_effective     <= n_effective_w;
        omega           <= omega_w;
        krim_count      <= krim_count_w;
        krim_score      <= krim_score_w;
        krim_recall     <= krim_recall_w;
        krim_commit_ok  <= krim_commit_ok_w;
        krim_commit_rej <= krim_commit_rej_w;
        debug_steer_field <= debug_steer_field_w;
    end

    // ---- ArcLoom Top Instance (Pure 9-Strand Kinematics) ----
    arcloom_top arcloom_inst (
        .clk(S_AXI_ACLK), .rst_n(S_AXI_ARESETN),
        .sensor_adc_front(sensor_adc_in),
        .sensor_valid_front(sensor_valid_in),
        .sensor_adc_left(hw_sensor_data_left[15:4]),
        .sensor_valid_left(hw_sensor_valid_left),
        .sensor_adc_right(hw_sensor_data_right[15:4]),
        .sensor_valid_right(hw_sensor_valid_right),
        .sensor_bl_front(sensor_bl_front),
        .sensor_bl_left(sensor_bl_left),
        .sensor_bl_right(sensor_bl_right),
        .sw_familiarity(sw_familiarity),
        .sw_fam_enable(sw_fam_enable),
        .sw_krim_commit(sw_krim_commit),
        .target_match_score(target_match_score_w),
        .decision_steer(decision_steer_w),
        .decision_speed(decision_speed_w),
        .decision_conf(decision_conf_w),
        .structural_lock(structural_lock_w),
        .dsf_safe_mode(dsf_safe_mode_w),
        .dsf_valid(dsf_valid_w),
        .dsf_D(dsf_D_w),
        .dsf_R_rev(dsf_R_rev_w),
        .loom_state(loom_state_w),
        .n_effective(n_effective_w),
        .omega(omega_w),
        .krimelack_count(krim_count_w),
        .krimelack_score(krim_score_w),
        .krimelack_recall_valid(krim_recall_w),
        .krimelack_commit_accepted(krim_commit_ok_w),
        .krimelack_commit_rejected(krim_commit_rej_w),
        .debug_steer_field(debug_steer_field_w)
    );

    // ---- MathLoom ALU (12-trit, combinational) ----
    wire [23:0] ml_sum_w;
    wire [1:0]  ml_carry_w;
    wire [47:0] ml_product_w;
    wire        ml_eq_w, ml_gt_w, ml_lt_w;

    arcloom_mathloom_alu mathloom_alu (
        .a(mathloom_a), .b(mathloom_b),
        .sum_out(ml_sum_w), .carry_out(ml_carry_w),
        .product_out(ml_product_w),
        .cmp_eq(ml_eq_w), .cmp_gt(ml_gt_w), .cmp_lt(ml_lt_w)
    );

    // ---- MathLoom Folding Division (12-trit, clocked) ----
    reg         div_start;
    wire [23:0] div_quotient, div_remainder;
    wire        div_done, div_by_zero;
    wire [18:0] div_cycles;
    reg  [23:0] div_quot_r, div_rem_r;
    reg         div_dbz_r;
    reg  [18:0] div_cyc_r;
    reg         div_result_ready;
    reg         div_pending;

    arcloom_mathloom_div div_inst (
        .clk(S_AXI_ACLK), .rst_n(S_AXI_ARESETN),
        .start(div_start),
        .a_in(mathloom_a), .b_in(mathloom_b),
        .quotient(div_quotient), .remainder(div_remainder),
        .done(div_done), .div_by_zero(div_by_zero),
        .cycle_count(div_cycles)
    );

    // Division latch
    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            div_quot_r       <= 24'd0;
            div_rem_r        <= 24'd0;
            div_dbz_r        <= 1'b0;
            div_cyc_r        <= 19'd0;
            div_result_ready <= 1'b0;
            div_pending      <= 1'b0;
        end else if (div_done && div_pending) begin
            div_quot_r       <= div_quotient;
            div_rem_r        <= div_remainder;
            div_dbz_r        <= div_by_zero;
            div_cyc_r        <= div_cycles;
            div_result_ready <= 1'b1;
            div_pending      <= 1'b0;
        end
    end

    // ---- AXI Write channel ----
    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            axi_bvalid        <= 1'b0;
            aw_pending        <= 1'b0;
            w_pending         <= 1'b0;
            axi_write_error   <= 1'b0;
            sw_sensor_adc     <= 12'd0;
            motor_enable      <= 1'b0;
            sw_krim_commit    <= 1'b0;
            sw_familiarity    <= 8'd0;
            sw_fam_enable     <= 1'b0;
            mathloom_a        <= 24'd0;
            mathloom_b        <= 24'd0;
            div_start         <= 1'b0;
            sensor_bl_front   <= 12'd0;
            sensor_bl_left    <= 12'd0;
            sensor_bl_right   <= 12'd0;
        end else begin
            div_start <= 1'b0;

            if (S_AXI_AWVALID && S_AXI_AWREADY) begin
                axi_awaddr <= S_AXI_AWADDR;
                aw_pending <= 1'b1;
            end
            if (S_AXI_WVALID && S_AXI_WREADY) begin
                axi_wdata <= S_AXI_WDATA;
                axi_wstrb <= S_AXI_WSTRB;
                w_pending <= 1'b1;
            end

            if (axi_bvalid && S_AXI_BREADY)
                axi_bvalid <= 1'b0;

            if (aw_pending && w_pending && !axi_bvalid) begin
                aw_pending <= 1'b0;
                w_pending  <= 1'b0;
                axi_bvalid <= 1'b1;
                axi_write_error <= (axi_wstrb != 4'hf);

                if (axi_wstrb == 4'hf) case (axi_awaddr[7:2])
                    6'd0: begin  // 0x00: sensor write
                        sw_sensor_adc <= axi_wdata[11:0];
                        if (axi_wdata[16])
                            sw_valid_stretch <= 3'd4;
                    end
                    6'd1: begin  // 0x04: mathloom A (24-bit)
                        if (!div_pending) begin
                            mathloom_a <= axi_wdata[23:0];
                            div_result_ready <= 1'b0;
                        end else axi_write_error <= 1'b1;
                    end
                    6'd2: begin  // 0x08: mathloom B (24-bit)
                        if (!div_pending) begin
                            mathloom_b <= axi_wdata[23:0];
                            div_result_ready <= 1'b0;
                        end else axi_write_error <= 1'b1;
                    end
                    6'd3: begin  // 0x0C: division trigger
                        if (axi_wdata[16] && !div_pending) begin
                            div_start        <= 1'b1;
                            div_pending      <= 1'b1;
                            div_result_ready <= 1'b0;
                            div_dbz_r        <= 1'b0;
                            div_cyc_r        <= 0;
                        end else if (axi_wdata[16]) axi_write_error <= 1'b1;
                    end
                    6'd4: begin  // 0x10: motor enable [2], krim commit [1]
                        motor_enable   <= axi_wdata[2];
                        sw_krim_commit <= axi_wdata[1];
                    end
                    6'd5: begin  // 0x14: familiarity override [7:0], enable [8]
                        sw_familiarity <= axi_wdata[7:0];
                        sw_fam_enable  <= axi_wdata[8];
                    end
                    6'd12: begin // 0x30: hardware distance baselines {left[27:16], front[11:0]}
                        sensor_bl_front <= axi_wdata[11:0];
                        sensor_bl_left  <= axi_wdata[27:16];
                    end
                    6'd13: begin // 0x34: hardware distance baseline right[11:0]
                        sensor_bl_right <= axi_wdata[11:0];
                    end
                endcase
            end

            // Latch MathLoom results every cycle
            ml_sum_r     <= ml_sum_w;
            ml_carry_r   <= ml_carry_w;
            ml_product_r <= ml_product_w;
            ml_eq_r      <= ml_eq_w;
            ml_gt_r      <= ml_gt_w;
            ml_lt_r      <= ml_lt_w;
        end
    end

    // ---- AXI Read channel ----
    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            axi_rvalid  <= 1'b0;
            axi_rdata   <= 0;
        end else begin
            if (S_AXI_ARVALID && S_AXI_ARREADY) begin
                axi_rvalid <= 1'b1;
                case (S_AXI_ARADDR[7:2])
                    // 0x00: Decision + status
                    6'd0: axi_rdata <= {18'd0,
                                        dsf_R_rev, dsf_D, dsf_valid,
                                        dsf_safe_mode, structural_lock,
                                        2'd0, decision_conf,
                                        decision_speed, decision_steer};

                    // 0x04: Loom state [31:0] (Decision [5:0], Context [11:6], Momentum [17:12])
                    6'd1: axi_rdata <= loom_state_r[0];

                    // 0x08: MathLoom ADD (12-trit) + compare
                    6'd2: axi_rdata <= {ml_lt_r, ml_gt_r, ml_eq_r,
                                        3'd0,
                                        ml_carry_r, ml_sum_r};

                    // 0x0C: MathLoom MUL or DIV (muxed)
                    6'd3: axi_rdata <= div_result_ready ?
                                        {6'd0, 1'b1, div_dbz_r, div_quot_r}
                                      : ml_product_r[31:0];

                    // 0x10: DIV remainder + cycles
                    6'd4: axi_rdata <= {div_cyc_r[7:0], div_rem_r};

                    // 0x14: MUL product high
                    6'd5: axi_rdata <= {16'd0, ml_product_r[47:32]};

                    // 0x1C: Left/Right sensor raw ADC
                    6'd7: axi_rdata <= {4'd0, right_adc_r, 4'd0, left_adc_r};

                    // 0x20: Krimelack status + target match
                    6'd8: axi_rdata <= {target_match_score_w,
                                        2'd0, krim_score[7:0],
                                        1'b0, krim_recall,
                                        krim_commit_ok, krim_commit_rej,
                                        4'd0, krim_count};

                    // 0x28: Front sensor raw ADC + motor_enable status
                    6'd10: axi_rdata <= {19'd0, motor_enable, live_adc};

                    // 0x30: Hardware distance baselines readback: Left [27:16], Front [11:0]
                    6'd12: axi_rdata <= {4'd0, sensor_bl_left, 4'd0, sensor_bl_front};

                    // 0x34: Hardware distance baseline readback: Right [11:0]
                    6'd13: axi_rdata <= {20'd0, sensor_bl_right};

                    // 0x40-0x54: Full 81-trit loom_state (6 registers)
                    6'd16: axi_rdata <= loom_state_r[0];
                    6'd17: axi_rdata <= loom_state_r[1];
                    6'd18: axi_rdata <= loom_state_r[2];
                    6'd19: axi_rdata <= loom_state_r[3];
                    6'd20: axi_rdata <= loom_state_r[4];
                    6'd21: axi_rdata <= loom_state_r[5];

                    // 0x74: Division cycle count
                    6'd29: axi_rdata <= {13'd0, div_cyc_r};

                    // 0x78: MathLoom ABI identifier (ABI v1)
                    6'd30: axi_rdata <= 32'h4D4C0001;

                    // 0x7C: Division status
                    6'd31: axi_rdata <= {29'd0, div_pending, div_dbz_r, div_result_ready};

                    default: axi_rdata <= 32'd0;
                endcase
            end else if (axi_rvalid && S_AXI_RREADY)
                axi_rvalid <= 1'b0;
        end
    end

    // ---- Motor control ----
    // Steer: 01=+1 (turn right), 10=-1 (turn left), 00=straight
    // Speed follows front distance polarity: close→+1→reverse, far→-1→forward
    // Motor A = left wheel, Motor B = right wheel
    wire go_fwd   = (decision_speed == 2'b01);
    wire go_rev   = (decision_speed == 2'b10);
    wire turn_r   = (decision_steer == 2'b10);
    wire turn_l   = (decision_steer == 2'b01);

    // Left wheel (motor A) — gated by motor_enable
    assign motor_ain1 = motor_enable & ((go_rev && !turn_r) || (turn_l));
    assign motor_ain2 = motor_enable & ((go_fwd && !turn_l) || (turn_r));

    // Right wheel (motor B) — gated by motor_enable
    assign motor_bin1 = motor_enable & ((go_rev && !turn_l) || (turn_r));
    assign motor_bin2 = motor_enable & ((go_fwd && !turn_r) || (turn_l));

endmodule
