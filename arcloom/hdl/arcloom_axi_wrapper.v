// ============================================================
// ArcLoom AXI-Lite Wrapper — 4 Registers, All Features
// ============================================================
//
// ADDR_WIDTH=4 (16 bytes, 4 registers). This is what the AXI
// interconnect actually supports on PYNQ Block Design.
//
// WRITE:
//   0x00: [11:0] sensor ADC, [16] valid pulse
//   0x04: [7:0] mathloom A operand
//   0x08: [7:0] mathloom B operand (triggers result latch)
//   0x0C: [5:0] cam_edge, [11:6] cam_motion
//
// READ:
//   0x00: Decision + flags
//   0x04: Loom state low 32 bits
//   0x08: MathLoom results (latched on B write):
//         [7:0] sum, [9:8] carry, [15:10] reserved,
//         [16] eq, [17] gt, [18] lt
//   0x0C: MathLoom multiply product [15:0], loom_state[47:32] in [31:16]
// ============================================================

module arcloom_axi_wrapper #(
    parameter C_S_AXI_DATA_WIDTH = 32,
    parameter C_S_AXI_ADDR_WIDTH = 4
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

    input  wire [15:0] hw_sensor_data,
    input  wire        hw_sensor_valid,

    // Motor drive outputs — directly from SPPU decision (no ARM)
    output wire        motor_ain1,    // Pmod A pin 0 (Y18)
    output wire        motor_ain2,    // Pmod A pin 1 (Y19)
    output wire        motor_bin1,    // Pmod A pin 2 (Y16)
    output wire        motor_bin2     // Pmod A pin 3 (Y17)
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
    reg [5:0]  cam_edge_reg, cam_motion_reg;
    reg [7:0]  mathloom_a, mathloom_b;

    // ---- Latched MathLoom results ----
    reg [7:0]  ml_sum_r;
    reg [1:0]  ml_carry_r;
    reg [15:0] ml_product_r;
    reg        ml_eq_r, ml_gt_r, ml_lt_r;

    wire sw_sensor_valid_pulse = (sw_valid_stretch != 3'd0);

    // ---- Hardware sensor mux ----
    wire [11:0] hw_adc = hw_sensor_data[15:4];
    wire [11:0] sensor_adc_mux   = hw_sensor_valid ? hw_adc : sw_sensor_adc;
    wire        sensor_valid_mux = hw_sensor_valid | sw_sensor_valid_pulse;

    reg [11:0] live_adc;
    always @(posedge S_AXI_ACLK)
        if (hw_sensor_valid) live_adc <= hw_adc;

    // ---- ArcLoom instance ----
    wire [1:0]  decision_steer, decision_speed, decision_conf;
    wire        structural_lock, dsf_safe_mode, dsf_valid;
    wire [1:0]  dsf_D;
    wire        dsf_R_rev;
    wire [47:0] loom_state;
    wire [4:0]  n_effective;
    wire [7:0]  omega;
    wire [5:0]  krim_count;
    wire [7:0]  krim_score;
    wire        krim_recall, krim_commit_ok, krim_commit_rej;

    arcloom_top arcloom_inst (
        .clk(S_AXI_ACLK), .rst_n(S_AXI_ARESETN),
        .sensor_adc(sensor_adc_mux), .sensor_valid(sensor_valid_mux),
        .cam_edge_strand(cam_edge_reg), .cam_motion_strand(cam_motion_reg),
        .decision_steer(decision_steer), .decision_speed(decision_speed),
        .decision_conf(decision_conf),
        .structural_lock(structural_lock), .dsf_safe_mode(dsf_safe_mode),
        .dsf_valid(dsf_valid), .dsf_D(dsf_D), .dsf_R_rev(dsf_R_rev),
        .loom_state(loom_state), .n_effective(n_effective), .omega(omega),
        .krimelack_count(krim_count), .krimelack_score(krim_score),
        .krimelack_recall_valid(krim_recall),
        .krimelack_commit_accepted(krim_commit_ok),
        .krimelack_commit_rejected(krim_commit_rej)
    );

    // ---- MathLoom ALU (combinational) ----
    wire [7:0]  ml_sum_w;
    wire [1:0]  ml_carry_w;
    wire [15:0] ml_product_w;
    wire        ml_eq_w, ml_gt_w, ml_lt_w;

    arcloom_mathloom_alu mathloom_alu (
        .a(mathloom_a), .b(mathloom_b),
        .sum_out(ml_sum_w), .carry_out(ml_carry_w),
        .product_out(ml_product_w),
        .cmp_eq(ml_eq_w), .cmp_gt(ml_gt_w), .cmp_lt(ml_lt_w)
    );

    // ---- MathLoom Folding Division (clocked — iterative) ----
    reg         div_start;
    wire [7:0]  div_quotient, div_remainder;
    wire        div_done, div_by_zero;
    wire [5:0]  div_cycles;
    reg  [7:0]  div_quot_r, div_rem_r;
    reg         div_dbz_r;
    reg  [5:0]  div_cyc_r;

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
            axi_awready    <= 1'b0;
            axi_wready     <= 1'b0;
            axi_bvalid     <= 1'b0;
            axi_awaddr     <= 0;
            sw_sensor_adc  <= 12'd0;
            sw_valid_stretch <= 3'd0;
            cam_edge_reg   <= 6'd0;
            cam_motion_reg <= 6'd0;
            mathloom_a     <= 8'd0;
            mathloom_b     <= 8'd0;
            ml_sum_r       <= 8'd0;
            ml_carry_r     <= 2'd0;
            ml_product_r   <= 16'd0;
            ml_eq_r        <= 1'b0;
            ml_gt_r        <= 1'b0;
            ml_lt_r        <= 1'b0;
            div_start      <= 1'b0;
            div_quot_r     <= 8'd0;
            div_rem_r      <= 8'd0;
            div_dbz_r      <= 1'b0;
            div_cyc_r      <= 6'd0;
        end else begin
            if (sw_valid_stretch != 3'd0)
                sw_valid_stretch <= sw_valid_stretch - 3'd1;

            // Latch division results when done
            div_start <= 1'b0;
            if (div_done) begin
                div_quot_r <= div_quotient;
                div_rem_r  <= div_remainder;
                div_dbz_r  <= div_by_zero;
                div_cyc_r  <= div_cycles;
            end

            if (~axi_awready && S_AXI_AWVALID && S_AXI_WVALID) begin
                axi_awready <= 1'b1;
                axi_awaddr  <= S_AXI_AWADDR;
            end else
                axi_awready <= 1'b0;

            if (~axi_wready && S_AXI_AWVALID && S_AXI_WVALID) begin
                axi_wready <= 1'b1;
                case (S_AXI_AWADDR[3:2])
                    2'd0: begin  // 0x00: sensor
                        sw_sensor_adc <= S_AXI_WDATA[11:0];
                        if (S_AXI_WDATA[16])
                            sw_valid_stretch <= 3'd4;
                    end
                    2'd1: begin  // 0x04: mathloom A
                        mathloom_a <= S_AXI_WDATA[7:0];
                    end
                    2'd2: begin  // 0x08: mathloom B + latch results
                        mathloom_b <= S_AXI_WDATA[7:0];
                        // Latch current ALU outputs (they'll settle
                        // combinationally from mathloom_a and the OLD
                        // mathloom_b - we latch NEXT cycle for new B)
                    end
                    2'd3: begin  // 0x0C: camera strands OR division trigger
                        if (S_AXI_WDATA[16]) begin
                            // Bit 16 set = trigger folding division using current A and B
                            div_start <= 1'b1;
                        end else begin
                            cam_edge_reg   <= S_AXI_WDATA[5:0];
                            cam_motion_reg <= S_AXI_WDATA[11:6];
                        end
                    end
                endcase
            end else
                axi_wready <= 1'b0;

            // Latch MathLoom results every cycle (they're combinational
            // from mathloom_a and mathloom_b, always valid)
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
                case (axi_araddr[3:2])
                    // 0x00: Decision + status
                    2'd0: axi_rdata <= {18'd0,
                                        dsf_R_rev, dsf_D, dsf_valid,
                                        dsf_safe_mode, structural_lock,
                                        2'd0, decision_conf,
                                        decision_speed, decision_steer};
                    // 0x04: Loom state [31:0]
                    2'd1: axi_rdata <= loom_state[31:0];
                    // 0x08: MathLoom ADD + COMPARE results
                    2'd2: axi_rdata <= {13'd0,
                                        ml_lt_r, ml_gt_r, ml_eq_r,
                                        6'd0,
                                        ml_carry_r, ml_sum_r};
                    // 0x0C: MathLoom MULTIPLY [15:0] + division results
                    //   [7:0]   = quotient
                    //   [15:8]  = remainder
                    //   [16]    = div_by_zero flag
                    //   [22:17] = cycle count
                    //   [23]    = division done (latched)
                    2'd3: axi_rdata <= {8'd0,
                                        1'b1,           // done flag (reading means done)
                                        div_cyc_r,
                                        div_dbz_r,
                                        div_rem_r,
                                        div_quot_r};
                endcase
            end else if (axi_rvalid && S_AXI_RREADY)
                axi_rvalid <= 1'b0;
        end
    end

    // ---- Motor control — combinational from SPPU decision ----
    // TB6612FNG: AIN1/AIN2 = motor A, BIN1/BIN2 = motor B
    //   1,0 = forward | 0,1 = reverse | 0,0 = stop
    //
    // Decision mapping:
    //   steer = +1 (01) → obstacle close → REVERSE both
    //   steer = null (00) → uncertain → STOP
    //   steer = -1 (10) → clear → STOP (safe for demo)
    assign motor_ain1 = 1'b0;                                    // never drive forward
    assign motor_ain2 = (decision_steer == 2'b01) ? 1'b1 : 1'b0; // reverse when obstacle
    assign motor_bin1 = 1'b0;
    assign motor_bin2 = (decision_steer == 2'b01) ? 1'b1 : 1'b0;

endmodule
