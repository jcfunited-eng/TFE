// ============================================================
// ArcLoom AXI-Lite Wrapper — 16 Registers
// ============================================================
//
// ADDR_WIDTH=6 (64 bytes, 16 registers).
// Expanded for 3 sensors, camera, 12-trit MathLoom.
//
// WRITE:
//   0x00: [11:0] sensor ADC (software), [16] valid pulse
//   0x04: [23:0] mathloom A operand (12-trit BT)
//   0x08: [23:0] mathloom B operand (triggers result latch)
//   0x0C: [5:0] cam_edge, [11:6] cam_motion, [16] div trigger
//   0x10: [0] krimelack clear, [1] krimelack commit request
//
// READ:
//   0x00: Decision + flags
//   0x04: Loom state [31:0]
//   0x08: MathLoom ADD: [23:0] sum, [25:24] carry, [28] eq, [29] gt, [30] lt
//   0x0C: MathLoom MUL/DIV (muxed by div_result_ready)
//         MUL: [31:0] product low 32 bits
//         DIV: [23:0] quotient, [24] div_by_zero, [25] done
//   0x10: DIV remainder [23:0] + cycle count [31:24]
//   0x14: MUL product high [15:0] + loom_state[47:32]
//   0x18: Camera line features [31:0]
//   0x1C: Left/Right sensor raw ADC [31:0]
//   0x20: Krimelack status [31:0]
//   0x24: Camera frame status
// ============================================================

module arcloom_axi_wrapper #(
    parameter C_S_AXI_DATA_WIDTH = 32,
    parameter C_S_AXI_ADDR_WIDTH = 6
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
    input  wire [15:0] hw_sensor_data,
    input  wire        hw_sensor_valid,
    input  wire [15:0] hw_sensor_data_left,
    input  wire        hw_sensor_valid_left,
    input  wire [15:0] hw_sensor_data_right,
    input  wire        hw_sensor_valid_right,

    // Camera line features from DVP capture
    input  wire [7:0]  cam_line_y_mean,
    input  wire [7:0]  cam_line_y_min,
    input  wire [7:0]  cam_line_y_max,
    input  wire [7:0]  cam_line_edge_count,
    input  wire [7:0]  cam_line_u_mean,
    input  wire [7:0]  cam_line_v_mean,
    input  wire [8:0]  cam_line_number,
    input  wire        cam_line_valid,
    input  wire        cam_frame_active,
    input  wire [7:0]  cam_frame_count,
    input  wire        cam_xclk_fb,       // Clock feedback — keeps Vivado from trimming cam_clk_0

    // Motor drive outputs
    output wire        motor_ain1,
    output wire        motor_ain2,
    output wire        motor_bin1,
    output wire        motor_bin2
);

    reg  axi_awready, axi_wready, axi_bvalid;
    reg  axi_arready, axi_rvalid;
    reg  [C_S_AXI_ADDR_WIDTH-1:0] axi_awaddr, axi_araddr;
    reg  [C_S_AXI_DATA_WIDTH-1:0] axi_rdata;

    assign S_AXI_AWREADY = axi_awready;
    assign S_AXI_WREADY  = axi_wready;
    assign S_AXI_BRESP   = 2'b00;
    assign S_AXI_BVALID  = axi_bvalid;
    assign S_AXI_ARREADY = axi_arready;
    assign S_AXI_RDATA   = axi_rdata;
    assign S_AXI_RRESP   = 2'b00;
    assign S_AXI_RVALID  = axi_rvalid;

    // ---- Write registers ----
    reg [11:0] sw_sensor_adc;
    reg [2:0]  sw_valid_stretch;
    reg        motor_enable;
    reg [7:0]  sw_familiarity;
    reg        sw_fam_enable;
    reg [23:0] mathloom_a, mathloom_b;

    // ---- Latched MathLoom results (12-trit) ----
    reg [23:0] ml_sum_r;
    reg [1:0]  ml_carry_r;
    reg [47:0] ml_product_r;
    reg        ml_eq_r, ml_gt_r, ml_lt_r;

    // ---- Latched camera line data ----
    reg [7:0]  cam_y_mean_r, cam_y_min_r, cam_y_max_r, cam_edge_cnt_r;
    reg [7:0]  cam_u_mean_r, cam_v_mean_r;
    reg [8:0]  cam_line_num_r;

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

    // Latch camera line data
    always @(posedge S_AXI_ACLK) begin
        if (cam_line_valid) begin
            cam_y_mean_r   <= cam_line_y_mean;
            cam_y_min_r    <= cam_line_y_min;
            cam_y_max_r    <= cam_line_y_max;
            cam_edge_cnt_r <= cam_line_edge_count;
            cam_u_mean_r   <= cam_line_u_mean;
            cam_v_mean_r   <= cam_line_v_mean;
            cam_line_num_r <= cam_line_number;
        end
    end

    // ---- ArcLoom instance (raw wires) ----
    wire [1:0]  decision_steer_w, decision_speed_w, decision_conf_w;
    wire        structural_lock_w, dsf_safe_mode_w, dsf_valid_w;
    wire [1:0]  dsf_D_w;
    wire        dsf_R_rev_w;
    wire [145:0] loom_state_w;
    wire [6:0]  n_effective_w;
    wire [7:0]  omega_w;
    wire [5:0]  krim_count_w;
    wire [7:0]  krim_score_w;
    wire        krim_recall_w, krim_commit_ok_w, krim_commit_rej_w;
    wire signed [31:0] debug_steer_field_w;

    // ---- Latched ArcLoom outputs (stable for AXI reads) ----
    reg [1:0]  decision_steer, decision_speed, decision_conf;
    reg        structural_lock, dsf_safe_mode, dsf_valid;
    reg [1:0]  dsf_D;
    reg        dsf_R_rev;
    reg [31:0] loom_state_lo;
    reg [5:0]  krim_count;
    reg [7:0]  krim_score;
    reg        krim_recall, krim_commit_ok, krim_commit_rej;
    reg signed [31:0] debug_steer_field;

    always @(posedge S_AXI_ACLK) begin
        decision_steer  <= decision_steer_w;
        decision_speed  <= decision_speed_w;
        decision_conf   <= decision_conf_w;
        structural_lock <= structural_lock_w;
        dsf_safe_mode   <= dsf_safe_mode_w;
        dsf_valid       <= dsf_valid_w;
        dsf_D           <= dsf_D_w;
        dsf_R_rev       <= dsf_R_rev_w;
        loom_state_lo   <= loom_state_w[31:0];
        krim_count      <= krim_count_w;
        krim_score      <= krim_score_w;
        krim_recall     <= krim_recall_w;
        krim_commit_ok  <= krim_commit_ok_w;
        krim_commit_rej <= krim_commit_rej_w;
        debug_steer_field <= debug_steer_field_w;
    end

    // ---- All 3 sensors pass raw ADC to arcloom_top ----
    // BSIL-BT conversion happens inside arcloom_top (3× arcloom_bsil_bt)
    // No threshold conversion in the wrapper — full gradient preserved.

    arcloom_top arcloom_inst (
        .clk(S_AXI_ACLK), .rst_n(S_AXI_ARESETN),
        .sensor_adc_front(hw_sensor_data[15:4]),
        .sensor_valid_front(hw_sensor_valid),
        .sensor_adc_left(hw_sensor_data_left[15:4]),
        .sensor_valid_left(hw_sensor_valid_left),
        .sensor_adc_right(hw_sensor_data_right[15:4]),
        .sensor_valid_right(hw_sensor_valid_right),
        .cam_y_mean(cam_y_mean_r),
        .cam_edge_count(cam_edge_cnt_r),
        .cam_u_mean(cam_u_mean_r),
        .cam_valid(cam_line_valid),
        .sw_familiarity(sw_familiarity),
        .sw_fam_enable(sw_fam_enable),
        .decision_steer(decision_steer_w), .decision_speed(decision_speed_w),
        .decision_conf(decision_conf_w),
        .structural_lock(structural_lock_w), .dsf_safe_mode(dsf_safe_mode_w),
        .dsf_valid(dsf_valid_w), .dsf_D(dsf_D_w), .dsf_R_rev(dsf_R_rev_w),
        .loom_state(loom_state_w), .n_effective(n_effective_w), .omega(omega_w),
        .krimelack_count(krim_count_w), .krimelack_score(krim_score_w),
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
    wire [17:0] div_cycles;
    reg  [23:0] div_quot_r, div_rem_r;
    reg         div_dbz_r;
    reg  [17:0] div_cyc_r;
    reg         div_result_ready;

    arcloom_mathloom_div div_inst (
        .clk(S_AXI_ACLK), .rst_n(S_AXI_ARESETN),
        .start(div_start),
        .a_in(mathloom_a), .b_in(mathloom_b),
        .quotient(div_quotient), .remainder(div_remainder),
        .done(div_done), .div_by_zero(div_by_zero),
        .cycle_count(div_cycles)
    );

    // ---- Write channel ----
    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            axi_awready      <= 1'b0;
            axi_wready       <= 1'b0;
            axi_bvalid       <= 1'b0;
            axi_awaddr       <= 0;
            sw_sensor_adc    <= 12'd0;
            sw_valid_stretch <= 3'd0;
            motor_enable     <= 1'b0;
            sw_familiarity   <= 8'd0;
            sw_fam_enable    <= 1'b0;
            mathloom_a       <= 24'd0;
            mathloom_b       <= 24'd0;
            ml_sum_r         <= 24'd0;
            ml_carry_r       <= 2'd0;
            ml_product_r     <= 48'd0;
            ml_eq_r          <= 1'b0;
            ml_gt_r          <= 1'b0;
            ml_lt_r          <= 1'b0;
            div_start        <= 1'b0;
            div_quot_r       <= 24'd0;
            div_rem_r        <= 24'd0;
            div_dbz_r        <= 1'b0;
            div_cyc_r        <= 18'd0;
            div_result_ready <= 1'b0;
        end else begin
            if (sw_valid_stretch != 3'd0)
                sw_valid_stretch <= sw_valid_stretch - 3'd1;

            div_start <= 1'b0;
            if (div_done) begin
                div_quot_r       <= div_quotient;
                div_rem_r        <= div_remainder;
                div_dbz_r        <= div_by_zero;
                div_cyc_r        <= div_cycles;
                div_result_ready <= 1'b1;
            end

            if (~axi_awready && S_AXI_AWVALID && S_AXI_WVALID) begin
                axi_awready <= 1'b1;
                axi_awaddr  <= S_AXI_AWADDR;
            end else
                axi_awready <= 1'b0;

            if (~axi_wready && S_AXI_AWVALID && S_AXI_WVALID) begin
                axi_wready <= 1'b1;
                case (S_AXI_AWADDR[5:2])
                    4'd0: begin  // 0x00: sensor
                        sw_sensor_adc <= S_AXI_WDATA[11:0];
                        if (S_AXI_WDATA[16])
                            sw_valid_stretch <= 3'd4;
                    end
                    4'd1: begin  // 0x04: mathloom A (24-bit)
                        mathloom_a <= S_AXI_WDATA[23:0];
                    end
                    4'd2: begin  // 0x08: mathloom B (24-bit) + latch
                        mathloom_b <= S_AXI_WDATA[23:0];
                        div_result_ready <= 1'b0;
                    end
                    4'd3: begin  // 0x0C: division trigger
                        if (S_AXI_WDATA[16])
                            div_start <= 1'b1;
                    end
                    4'd4: begin  // 0x10: motor enable [2]
                        motor_enable <= S_AXI_WDATA[2];
                    end
                    4'd5: begin  // 0x14: familiarity override [7:0], enable [8]
                        sw_familiarity <= S_AXI_WDATA[7:0];
                        sw_fam_enable  <= S_AXI_WDATA[8];
                    end
                endcase
            end else
                axi_wready <= 1'b0;

            // Latch MathLoom results every cycle
            ml_sum_r     <= ml_sum_w;
            ml_carry_r   <= ml_carry_w;
            ml_product_r <= ml_product_w;
            ml_eq_r      <= ml_eq_w;
            ml_gt_r      <= ml_gt_w;
            ml_lt_r      <= ml_lt_w;

            if (axi_awready && S_AXI_AWVALID && axi_wready && S_AXI_WVALID && ~axi_bvalid)
                axi_bvalid <= 1'b1;
            else if (S_AXI_BREADY && axi_bvalid)
                axi_bvalid <= 1'b0;
        end
    end

    // ---- Read channel ----
    always @(posedge S_AXI_ACLK) begin
        if (!S_AXI_ARESETN) begin
            axi_arready <= 1'b0;
            axi_rvalid  <= 1'b0;
            axi_rdata   <= 0;
            axi_araddr  <= 0;
        end else begin
            if (~axi_arready && S_AXI_ARVALID) begin
                axi_arready <= 1'b1;
                axi_araddr  <= S_AXI_ARADDR;
            end else
                axi_arready <= 1'b0;

            if (axi_arready && S_AXI_ARVALID && ~axi_rvalid) begin
                axi_rvalid <= 1'b1;
                case (axi_araddr[5:2])
                    // 0x00: Decision + status
                    4'd0: axi_rdata <= {18'd0,
                                        dsf_R_rev, dsf_D, dsf_valid,
                                        dsf_safe_mode, structural_lock,
                                        2'd0, decision_conf,
                                        decision_speed, decision_steer};
                    // 0x04: Loom state [31:0]
                    4'd1: axi_rdata <= loom_state_lo;

                    // 0x08: MathLoom ADD (12-trit) + compare
                    4'd2: axi_rdata <= {ml_lt_r, ml_gt_r, ml_eq_r,
                                        3'd0,
                                        ml_carry_r, ml_sum_r};

                    // 0x0C: MathLoom MUL or DIV (muxed)
                    4'd3: axi_rdata <= div_result_ready ?
                                        {6'd0, 1'b1, div_dbz_r, div_quot_r}
                                      : ml_product_r[31:0];

                    // 0x10: DIV remainder + cycles
                    4'd4: axi_rdata <= {div_cyc_r[7:0], div_rem_r};

                    // 0x14: MUL product high
                    4'd5: axi_rdata <= {16'd0, ml_product_r[47:32]};

                    // 0x18: Camera line features
                    4'd6: axi_rdata <= {cam_edge_cnt_r, cam_y_max_r,
                                        cam_y_min_r, cam_y_mean_r};

                    // 0x1C: Left/Right sensor raw ADC
                    4'd7: axi_rdata <= {4'd0, right_adc_r, 4'd0, left_adc_r};

                    // 0x20: Krimelack status
                    4'd8: axi_rdata <= {16'd0,
                                        krim_commit_rej, krim_commit_ok,
                                        krim_recall,
                                        1'b0,
                                        krim_score[7:0],
                                        2'd0, krim_count};

                    // 0x24: Camera frame status + line number + xclk feedback
                    4'd9: axi_rdata <= {13'd0, cam_xclk_fb,
                                        cam_frame_active, cam_frame_count,
                                        cam_line_num_r};

                    // 0x28: Front sensor raw ADC + motor_enable status
                    4'd10: axi_rdata <= {19'd0, motor_enable, live_adc};

                    // 0x2C: Debug — raw steer field value (signed 32-bit)
                    4'd11: axi_rdata <= debug_steer_field;

                    // 0x30: Camera color (U/V chrominance)
                    4'd12: axi_rdata <= {16'd0, cam_v_mean_r, cam_u_mean_r};

                    default: axi_rdata <= 32'd0;
                endcase
            end else if (axi_rvalid && S_AXI_RREADY)
                axi_rvalid <= 1'b0;
        end
    end

    // ---- Motor control ----
    // Steer: 01=+1 (turn right), 10=-1 (turn left), 00=straight
    // Speed follows front distance polarity: close→+1→reverse, far→-1→forward
    // No latch — decision goes directly to motors. Stability comes from
    // correct feedback gain, not clock sampling.
    //
    // Motor A = left wheel, Motor B = right wheel
    // AIN1=fwd, AIN2=rev for motor A
    // BIN1=fwd, BIN2=rev for motor B

    wire go_fwd   = (decision_speed == 2'b01);
    wire go_rev   = (decision_speed == 2'b10);
    wire turn_r   = (decision_steer == 2'b10);  // swapped: physical motors are opposite documented
    wire turn_l   = (decision_steer == 2'b01);  // swapped: physical motors are opposite documented

    // Left wheel (motor A) — gated by motor_enable
    // Physical wires AIN1/AIN2 swapped on TB6612FNG: AIN1=rev, AIN2=fwd
    assign motor_ain1 = motor_enable & ((go_rev && !turn_r) || (turn_l));
    assign motor_ain2 = motor_enable & ((go_fwd && !turn_l) || (turn_r));

    // Right wheel (motor B) — gated by motor_enable
    // Swapped to match left motor physical wiring orientation
    assign motor_bin1 = motor_enable & ((go_rev && !turn_l) || (turn_r));
    assign motor_bin2 = motor_enable & ((go_fwd && !turn_r) || (turn_l));

endmodule
