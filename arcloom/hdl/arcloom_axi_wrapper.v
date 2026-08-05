// ============================================================
// ArcLoom AXI-Lite Wrapper — 16 Registers
// ============================================================
//
// ADDR_WIDTH=8 (256 bytes, 64 registers).
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
    // Frame-level features (owl trick — upper/lower split)
    input  wire [7:0]  cam_frame_y_upper,
    input  wire [7:0]  cam_frame_y_lower,
    input  wire [7:0]  cam_frame_edge_upper,
    input  wire [7:0]  cam_frame_edge_lower,
    input  wire [7:0]  cam_frame_u_upper,
    input  wire [7:0]  cam_frame_u_lower,
    input  wire [7:0]  cam_frame_density,

    // I2C monitor read port (monitor lives inside cam_i2c_0)
    output wire [9:0]  i2c_mon_addr_out,
    input  wire [31:0] i2c_mon_data_in,
    input  wire [9:0]  i2c_mon_count_in,
    input  wire        i2c_mon_overflow_in,

    // Snapshot buffer interface (module in block design)
    output wire        snapshot_trigger_out,
    output wire [10:0] snapshot_rd_addr_out,
    input  wire        snapshot_done_ext,
    input  wire        snapshot_busy_ext,
    input  wire [31:0] snapshot_data_ext,

    // Runtime I2C write interface (to cam_i2c_0 in block design)
    output wire [15:0] i2c_rt_addr,
    output wire [7:0]  i2c_rt_data,
    output wire        i2c_rt_write,
    output wire        i2c_rt_read,
    input  wire        i2c_rt_busy,
    input  wire        i2c_rt_done,
    input  wire [7:0]  i2c_rt_read_data,
    input  wire        i2c_rt_read_valid,

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
    reg        sw_krim_commit;  // software Krimelack commit request
    reg        snapshot_trigger; // pulse: capture one frame to BRAM
    // Runtime I2C camera control
    reg [15:0] i2c_reg_addr;
    reg [7:0]  i2c_reg_data;
    reg        i2c_write_trigger;
    reg        i2c_read_trigger;
    // I2C read result latch
    reg [7:0]  i2c_read_result;
    reg        i2c_read_done;
    // Runtime camera baselines (written by Python at startup)
    reg [7:0]  cam_bl_y;       // Y mean baseline
    reg [7:0]  cam_bl_edge;    // Edge count baseline
    reg [7:0]  cam_bl_u;       // U chrominance baseline
    reg [7:0]  cam_bl_density; // Structural density baseline
    // Target motif for hunt/inspect (210-bit, 7 AXI writes)
    reg [31:0] target_motif_0;   // target_motif[31:0]
    reg [31:0] target_motif_1;   // target_motif[63:32]
    reg [31:0] target_motif_2;   // target_motif[95:64]
    reg [31:0] target_motif_3;   // target_motif[127:96]
    reg [31:0] target_motif_4;   // target_motif[159:128]
    reg [31:0] target_motif_5;   // target_motif[191:160]
    reg [17:0] target_motif_6;   // target_motif[209:192]
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
    wire [209:0] loom_state_w;
    wire [6:0]  n_effective_w;
    wire [7:0]  omega_w;
    wire [5:0]  krim_count_w;
    wire [7:0]  target_match_score_w;
    wire [7:0]  krim_score_w;
    wire        krim_recall_w, krim_commit_ok_w, krim_commit_rej_w;
    wire signed [31:0] debug_steer_field_w;

    // ---- Latched ArcLoom outputs (stable for AXI reads) ----
    reg [1:0]  decision_steer, decision_speed, decision_conf;
    reg        structural_lock, dsf_safe_mode, dsf_valid;
    reg [1:0]  dsf_D;
    reg        dsf_R_rev;
    reg [31:0] loom_state_r [0:6];  // 7 × 32-bit = 224 bits (covers 210)
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
        loom_state_r[0] <= loom_state_w[31:0];
        loom_state_r[1] <= loom_state_w[63:32];
        loom_state_r[2] <= loom_state_w[95:64];
        loom_state_r[3] <= loom_state_w[127:96];
        loom_state_r[4] <= loom_state_w[159:128];
        loom_state_r[5] <= loom_state_w[191:160];
        loom_state_r[6] <= {14'd0, loom_state_w[209:192]};
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
        .cam_y_upper(cam_frame_y_upper),
        .cam_y_lower(cam_frame_y_lower),
        .cam_edge_upper(cam_frame_edge_upper),
        .cam_edge_lower(cam_frame_edge_lower),
        .cam_u_upper(cam_frame_u_upper),
        .cam_u_lower(cam_frame_u_lower),
        .cam_density(cam_frame_density),
        .sw_familiarity(sw_familiarity),
        .sw_fam_enable(sw_fam_enable),
        .sw_krim_commit(sw_krim_commit),
        .cam_bl_y(cam_bl_y),
        .cam_bl_edge(cam_bl_edge),
        .cam_bl_u(cam_bl_u),
        .cam_bl_density(cam_bl_density),
        .target_match_score(target_match_score_w),
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
            sw_krim_commit    <= 1'b0;
            snapshot_trigger  <= 1'b0;
            snapshot_rd_addr  <= 11'd0;
            i2c_mon_rd_addr   <= 10'd0;
            i2c_reg_addr      <= 16'd0;
            i2c_reg_data      <= 8'd0;
            i2c_write_trigger <= 1'b0;
            i2c_read_trigger  <= 1'b0;
            i2c_read_result   <= 8'd0;
            i2c_read_done     <= 1'b0;
            cam_bl_y         <= 8'd0;
            cam_bl_edge      <= 8'd0;
            cam_bl_u         <= 8'd0;
            cam_bl_density   <= 8'd0;
            target_motif_0   <= 32'd0;
            target_motif_1   <= 32'd0;
            target_motif_2   <= 32'd0;
            target_motif_3   <= 32'd0;
            target_motif_4   <= 32'd0;
            target_motif_5   <= 32'd0;
            target_motif_6   <= 18'd0;
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

            // Auto-clear pulses after one cycle
            if (sw_krim_commit)
                sw_krim_commit <= 1'b0;
            if (snapshot_trigger)
                snapshot_trigger <= 1'b0;
            if (i2c_write_trigger)
                i2c_write_trigger <= 1'b0;
            if (i2c_read_trigger)
                i2c_read_trigger <= 1'b0;

            // Latch I2C read result when it arrives
            if (i2c_rt_read_valid) begin
                i2c_read_result <= i2c_rt_read_data;
                i2c_read_done   <= 1'b1;
            end

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
                case (S_AXI_AWADDR[7:2])
                    6'd0: begin  // 0x00: sensor
                        sw_sensor_adc <= S_AXI_WDATA[11:0];
                        if (S_AXI_WDATA[16])
                            sw_valid_stretch <= 3'd4;
                    end
                    6'd1: begin  // 0x04: mathloom A (24-bit)
                        mathloom_a <= S_AXI_WDATA[23:0];
                    end
                    6'd2: begin  // 0x08: mathloom B (24-bit) + latch
                        mathloom_b <= S_AXI_WDATA[23:0];
                        div_result_ready <= 1'b0;
                    end
                    6'd3: begin  // 0x0C: division trigger
                        if (S_AXI_WDATA[16])
                            div_start <= 1'b1;
                    end
                    6'd4: begin  // 0x10: motor enable [2], krimelack commit [1]
                        motor_enable <= S_AXI_WDATA[2];
                        sw_krim_commit <= S_AXI_WDATA[1];
                    end
                    6'd5: begin  // 0x14: familiarity override [7:0], enable [8]
                        sw_familiarity <= S_AXI_WDATA[7:0];
                        sw_fam_enable  <= S_AXI_WDATA[8];
                    end
                    6'd16: target_motif_0 <= S_AXI_WDATA;          // 0x40
                    6'd17: target_motif_1 <= S_AXI_WDATA;          // 0x44
                    6'd18: target_motif_2 <= S_AXI_WDATA;          // 0x48
                    6'd19: target_motif_3 <= S_AXI_WDATA;          // 0x4C
                    6'd20: target_motif_4 <= S_AXI_WDATA;          // 0x50
                    6'd21: target_motif_5 <= S_AXI_WDATA;          // 0x54
                    6'd22: begin                                    // 0x58
                        target_motif_6 <= S_AXI_WDATA[17:0];
                    end
                    6'd23: begin  // 0x5C: snapshot trigger [0], read addr [12:2]
                        snapshot_trigger <= S_AXI_WDATA[0];
                        snapshot_rd_addr <= S_AXI_WDATA[12:2];
                    end
                    6'd26: begin  // 0x68: I2C monitor read address [9:0]
                        i2c_mon_rd_addr <= S_AXI_WDATA[9:0];
                    end
                    6'd25: begin  // 0x64: I2C camera write {trigger[24], data[23:16], addr[15:0]}
                        i2c_reg_addr      <= S_AXI_WDATA[15:0];
                        i2c_reg_data      <= S_AXI_WDATA[23:16];
                        i2c_write_trigger <= S_AXI_WDATA[24];
                    end
                    6'd15: begin  // 0x3C: camera baselines {density, u, edge, y}
                        cam_bl_y       <= S_AXI_WDATA[7:0];
                        cam_bl_edge    <= S_AXI_WDATA[15:8];
                        cam_bl_u       <= S_AXI_WDATA[23:16];
                        cam_bl_density <= S_AXI_WDATA[31:24];
                    end
                    6'd28: begin  // 0x70: I2C read request {addr[15:0]}
                        i2c_reg_addr     <= S_AXI_WDATA[15:0];
                        i2c_read_trigger <= 1'b1;
                        i2c_read_done    <= 1'b0;  // clear done flag
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
                case (axi_araddr[7:2])
                    // 0x00: Decision + status
                    6'd0: axi_rdata <= {18'd0,
                                        dsf_R_rev, dsf_D, dsf_valid,
                                        dsf_safe_mode, structural_lock,
                                        2'd0, decision_conf,
                                        decision_speed, decision_steer};
                    // 0x04: Loom state [31:0]
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
                    // 0x14: MUL product high
                    6'd5: axi_rdata <= {16'd0, ml_product_r[47:32]};

                    // 0x18: Camera line features
                    6'd6: axi_rdata <= {cam_edge_cnt_r, cam_y_max_r,
                                        cam_y_min_r, cam_y_mean_r};

                    // 0x1C: Left/Right sensor raw ADC
                    6'd7: axi_rdata <= {4'd0, right_adc_r, 4'd0, left_adc_r};

                    // 0x20: Krimelack status + target match
                    // [31:24] target_match_score, [23:22] pad, [21:14] krim_score,
                    // [13] pad, [12] recall, [11] commit_ok, [10] commit_rej,
                    // [9:6] pad, [5:0] krim_count
                    6'd8: axi_rdata <= {target_match_score_w,
                                        2'd0, krim_score[7:0],
                                        1'b0, krim_recall,
                                        krim_commit_ok, krim_commit_rej,
                                        4'd0, krim_count};

                    // 0x24: Camera frame status + line number + xclk feedback
                    6'd9: axi_rdata <= {13'd0, cam_xclk_fb,
                                        cam_frame_active, cam_frame_count,
                                        cam_line_num_r};

                    // 0x28: Front sensor raw ADC + motor_enable status
                    6'd10: axi_rdata <= {19'd0, motor_enable, live_adc};

                    // 0x2C: Debug — raw steer field value (signed 32-bit)
                    6'd11: axi_rdata <= debug_steer_field;

                    // 0x30: Camera color (U/V chrominance)
                    6'd12: axi_rdata <= {16'd0, cam_v_mean_r, cam_u_mean_r};

                    // 0x34: Frame features — upper/lower Y and edge (owl trick)
                    6'd13: axi_rdata <= {cam_frame_edge_lower, cam_frame_edge_upper,
                                         cam_frame_y_lower, cam_frame_y_upper};

                    // 0x38: Frame features — upper/lower U + structural density
                    6'd14: axi_rdata <= {cam_frame_density, 8'd0,
                                         cam_frame_u_lower, cam_frame_u_upper};

                    // 0x40-0x58: Full loom_state (7 registers, 210 bits)
                    6'd16: axi_rdata <= loom_state_r[0];
                    6'd17: axi_rdata <= loom_state_r[1];
                    6'd18: axi_rdata <= loom_state_r[2];
                    6'd19: axi_rdata <= loom_state_r[3];
                    6'd20: axi_rdata <= loom_state_r[4];
                    6'd21: axi_rdata <= loom_state_r[5];
                    6'd22: axi_rdata <= loom_state_r[6];

                    // 0x5C: Snapshot status {done, busy}
                    6'd23: axi_rdata <= {30'd0, snapshot_busy_w, snapshot_done_w};

                    // 0x60: Snapshot BRAM read data (set addr via write to 0x5C)
                    6'd24: axi_rdata <= snapshot_rd_data;

                    // 0x64: I2C runtime status {done, busy}
                    6'd25: axi_rdata <= {30'd0, i2c_rt_busy, i2c_rt_done};

                    // 0x68: I2C monitor data (set addr via write to 0x68)
                    6'd26: axi_rdata <= i2c_mon_rd_data;

                    // 0x6C: I2C monitor status {overflow, write_count}
                    6'd27: axi_rdata <= {21'd0, i2c_mon_overflow, i2c_mon_write_count};

                    // 0x70: I2C read result {done[9], busy[8], data[7:0]}
                    6'd28: axi_rdata <= {22'd0, i2c_read_done, i2c_rt_busy, i2c_read_result};

                    default: axi_rdata <= 32'd0;
                endcase
            end else if (axi_rvalid && S_AXI_RREADY)
                axi_rvalid <= 1'b0;
        end
    end

    // ---- I2C Bus Monitor (lives inside cam_i2c_0, read port here) ----
    reg  [9:0]  i2c_mon_rd_addr;
    wire [31:0] i2c_mon_rd_data = i2c_mon_data_in;
    wire [9:0]  i2c_mon_write_count = i2c_mon_count_in;
    wire        i2c_mon_overflow = i2c_mon_overflow_in;
    assign i2c_mon_addr_out = i2c_mon_rd_addr;

    // ---- Snapshot buffer (external module in block design) ----
    reg  [10:0] snapshot_rd_addr;
    wire [31:0] snapshot_rd_data = snapshot_data_ext;
    wire        snapshot_done_w = snapshot_done_ext;
    wire        snapshot_busy_w = snapshot_busy_ext;
    assign snapshot_trigger_out = snapshot_trigger;
    assign snapshot_rd_addr_out = snapshot_rd_addr;
    assign i2c_rt_addr  = i2c_reg_addr;
    assign i2c_rt_data  = i2c_reg_data;
    assign i2c_rt_write = i2c_write_trigger;
    assign i2c_rt_read  = i2c_read_trigger;

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
