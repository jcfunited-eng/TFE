// ============================================================
// ArcLoom OV5640 I2C Configuration — Full QVGA DVP Init
// ============================================================
//
// Known-good register set for OV5640 QVGA 320x240 YUV422 DVP.
// Based on OV5640 application note + Linux driver defaults.
//
// Groups:
//   1. System/PLL — clock tree
//   2. Timing — sensor window, HTS/VTS (controls integration time)
//   3. Subsample — 2592x1944 sensor → 320x240 output
//   4. ISP — image processing enables
//   5. AEC/AGC — auto exposure/gain for usable brightness
//   6. Format — YUV422 DVP output
//   7. DVP — pin enables
//
// I2C address: 0x3C (7-bit), or 0x78/0x79 (8-bit R/W)
// OV5640 uses 16-bit register addresses + 8-bit data.
// Runs once on reset, then goes idle.
//
// Target: PYNQ-Z2 (XC7Z020-1CLG400C)
// ============================================================

module arcloom_cam_i2c (
    input  wire        clk,        // system clock (100MHz)
    input  wire        rst_n,

    // I2C pins (directly mapped to AR SDA/SCL)
    output reg         sda_out,    // SDA drive value
    output reg         sda_oe,     // SDA output enable (1=driving)
    input  wire        sda_in,     // SDA read value
    output reg         scl_out,    // SCL drive value
    output reg         scl_oe,     // SCL output enable (1=driving)

    // Status
    output reg         init_done,  // pulses when initialization complete
    output reg  [6:0]  init_step   // current init register being written
);

    // I2C clock: 100MHz / 1000 = 100kHz
    localparam CLK_DIV = 500;  // half-period count
    localparam ADDR_W  = 8'h78; // OV5640 write address (0x3C << 1)

    // ---- Init register table ----
    // Format: {16-bit addr, 8-bit data}
    localparam NUM_REGS = 56;

    reg [23:0] init_regs [0:NUM_REGS-1];

    initial begin
        // ======== 1. SYSTEM ========
        init_regs[0]  = {16'h3103, 8'h11};  // Clock from PLL
        init_regs[1]  = {16'h3008, 8'h82};  // Software reset (delay after)

        // ======== 2. PLL ========
        // XCLK=25MHz, PCLK target ~36MHz for QVGA
        init_regs[2]  = {16'h3034, 8'h1A};  // PLL charge pump, MIPI 10-bit
        init_regs[3]  = {16'h3035, 8'h21};  // System clk div: PLL/2 (was /1)
        init_regs[4]  = {16'h3036, 8'h46};  // PLL multiplier = 70
        init_regs[5]  = {16'h3037, 8'h13};  // PLL root div /1, pre-div /3
        init_regs[6]  = {16'h3108, 8'h01};  // PCLK root div /2
        init_regs[7]  = {16'h3824, 8'h01};  // DVP PCLK divider

        // ======== 3. TIMING — sensor window (center crop for ~80° FOV) ========
        // Full sensor: 2592x1944. Center half: 656-1968 x 486-1458
        // 2x zoom from 160° fish eye — object fills more of the frame
        // Output still 320x240 via subsampling
        init_regs[8]  = {16'h3800, 8'h02};  // X start high
        init_regs[9]  = {16'h3801, 8'h90};  // X start low = 656
        init_regs[10] = {16'h3802, 8'h01};  // Y start high
        init_regs[11] = {16'h3803, 8'hE6};  // Y start low = 486
        init_regs[12] = {16'h3804, 8'h07};  // X end high
        init_regs[13] = {16'h3805, 8'hB0};  // X end low = 1968
        init_regs[14] = {16'h3806, 8'h05};  // Y end high
        init_regs[15] = {16'h3807, 8'hB2};  // Y end low = 1458

        // ======== 4. OUTPUT SIZE ========
        init_regs[16] = {16'h3808, 8'h01};  // X output high
        init_regs[17] = {16'h3809, 8'h40};  // X output low = 320
        init_regs[18] = {16'h380A, 8'h00};  // Y output high
        init_regs[19] = {16'h380B, 8'hF0};  // Y output low = 240

        // ======== 5. HTS/VTS — total line/frame size ========
        // Controls integration time. THIS is why exposure was stuck.
        init_regs[20] = {16'h380C, 8'h07};  // HTS high
        init_regs[21] = {16'h380D, 8'h68};  // HTS low = 1896
        init_regs[22] = {16'h380E, 8'h03};  // VTS high
        init_regs[23] = {16'h380F, 8'hD8};  // VTS low = 984

        // ======== 6. ISP OFFSET ========
        init_regs[24] = {16'h3810, 8'h00};  // X offset high
        init_regs[25] = {16'h3811, 8'h10};  // X offset low = 16
        init_regs[26] = {16'h3812, 8'h00};  // Y offset high
        init_regs[27] = {16'h3813, 8'h06};  // Y offset low = 6

        // ======== 7. SUBSAMPLE ========
        init_regs[28] = {16'h3814, 8'h31};  // X subsample odd inc = 3, even = 1
        init_regs[29] = {16'h3815, 8'h31};  // Y subsample odd inc = 3, even = 1
        init_regs[30] = {16'h3820, 8'h41};  // Timing: vertical subsample
        init_regs[31] = {16'h3821, 8'h07};  // Timing: horizontal mirror + subsample

        // ======== 8. BLC (black level) ========
        init_regs[32] = {16'h4002, 8'h45};  // BLC: auto, 4-line target
        init_regs[33] = {16'h4005, 8'h18};  // BLC: update always

        // ======== 9. ISP ENABLE ========
        init_regs[34] = {16'h5000, 8'hA7};  // ISP: lenc, gamma, AWB, BLC, AEC
        init_regs[35] = {16'h5001, 8'hA3};  // ISP: SDE, scale, UV avg, color matrix, AWB
        init_regs[36] = {16'h501F, 8'h00};  // Format mux: ISP output = YUV

        // ======== 10. AEC/AGC with 60Hz flicker band filter ========
        // Indoor fluorescent lights flicker at 2× mains frequency (120Hz for US 60Hz).
        // Without band filtering, exposure spans non-integer flicker periods,
        // producing alternating bright/dark frames that dominate structural data.
        // Band filter synchronizes exposure to mains period — standard indoor setup.
        init_regs[37] = {16'h3C01, 8'h80};  // Enable auto 50/60Hz band detection
        init_regs[38] = {16'h3A00, 8'h7C};  // AEC: band ON, band auto, gain step, gain, exposure
        init_regs[39] = {16'h3503, 8'h02};  // Manual AGC (bit1=1), auto AEC (bit0=0)
        init_regs[40] = {16'h3A08, 8'h01};  // B50 step high
        init_regs[41] = {16'h3A09, 8'h27};  // B50 step low = 295
        init_regs[42] = {16'h3A0A, 8'h00};  // B60 step high
        init_regs[43] = {16'h3A0B, 8'hF6};  // B60 step low = 246
        init_regs[44] = {16'h3A0D, 8'h08};  // B50 max step count
        init_regs[45] = {16'h3A0E, 8'h06};  // B60 max step count
        init_regs[46] = {16'h3A0F, 8'h58};  // Stable range high = 88
        init_regs[47] = {16'h3A10, 8'h50};  // Stable range low = 80
        init_regs[48] = {16'h3A1B, 8'h58};  // Fast zone high = 88
        init_regs[49] = {16'h3A1E, 8'h50};  // Fast zone low = 80
        init_regs[50] = {16'h350A, 8'h00};  // Manual gain high = 0
        init_regs[51] = {16'h350B, 8'h10};  // Manual gain low = 16 (1.0x gain)

        // ======== 11. OUTPUT FORMAT ========
        init_regs[52] = {16'h4300, 8'h30};  // YUV422, YUYV order

        // ======== 12. DVP ENABLE ========
        init_regs[53] = {16'h3017, 8'hFF};  // DVP data pins enable
        init_regs[54] = {16'h3018, 8'hFF};  // DVP control pins enable
        init_regs[55] = {16'h3019, 8'h00};  // DVP PCLK polarity: normal
    end

    // ---- I2C state machine ----
    reg [15:0] clk_cnt;
    reg [4:0]  bit_cnt;
    reg [5:0]  reg_idx;
    reg [3:0]  state;
    reg [23:0] shift_reg;  // addr_hi, addr_lo, data
    reg [19:0] wait_cnt;   // 2^20 = ~10ms at 100MHz (OV5640 needs 5ms after reset)

    localparam S_IDLE     = 4'd0;
    localparam S_WAIT     = 4'd1;  // post-reset delay
    localparam S_START    = 4'd2;
    localparam S_ADDR     = 4'd3;  // send device address byte
    localparam S_ACK1     = 4'd4;
    localparam S_REG_HI   = 4'd5;  // send register address high byte
    localparam S_ACK2     = 4'd6;
    localparam S_REG_LO   = 4'd7;  // send register address low byte
    localparam S_ACK3     = 4'd8;
    localparam S_DATA     = 4'd9;  // send data byte
    localparam S_ACK4     = 4'd10;
    localparam S_STOP     = 4'd11;
    localparam S_NEXT     = 4'd12;
    localparam S_DONE     = 4'd13;

    // SCL/SDA timing
    reg scl_phase;  // 0=low, 1=high

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state     <= S_IDLE;
            sda_out   <= 1'b1;
            sda_oe    <= 1'b0;
            scl_out   <= 1'b1;
            scl_oe    <= 1'b0;
            init_done <= 1'b0;
            init_step <= 4'd0;
            clk_cnt   <= 16'd0;
            bit_cnt   <= 5'd0;
            reg_idx   <= 6'd0;
            shift_reg <= 24'd0;
            wait_cnt  <= 20'd0;
            scl_phase <= 1'b0;
        end else begin
            init_done <= 1'b0;

            case (state)
                S_IDLE: begin
                    // Start init sequence
                    sda_oe  <= 1'b1;
                    scl_oe  <= 1'b1;
                    sda_out <= 1'b1;
                    scl_out <= 1'b1;
                    reg_idx <= 6'd0;
                    wait_cnt <= 16'd0;
                    state   <= S_WAIT;
                end

                S_WAIT: begin
                    // Wait for camera to power up (20ms at 100MHz = 2M cycles)
                    wait_cnt <= wait_cnt + 20'd1;
                    if (wait_cnt == 20'hFFFFF) begin
                        if (reg_idx == 6'd2) begin
                            // Extra delay after software reset
                            state <= S_START;
                        end else begin
                            state <= S_START;
                        end
                    end
                end

                S_START: begin
                    // I2C start: SDA falls while SCL high
                    clk_cnt <= clk_cnt + 16'd1;
                    if (clk_cnt < CLK_DIV) begin
                        scl_out <= 1'b1;
                        sda_out <= 1'b0;  // SDA low = start
                    end else if (clk_cnt < CLK_DIV * 2) begin
                        scl_out <= 1'b0;  // SCL low
                    end else begin
                        clk_cnt   <= 16'd0;
                        shift_reg <= init_regs[reg_idx];
                        bit_cnt   <= 5'd7;
                        state     <= S_ADDR;
                        init_step <= reg_idx;
                    end
                end

                S_ADDR: begin
                    // Send 8-bit device address (0x78 = write)
                    clk_cnt <= clk_cnt + 16'd1;
                    if (clk_cnt == 0) begin
                        sda_out <= ADDR_W[bit_cnt[2:0]];
                        scl_out <= 1'b0;
                    end else if (clk_cnt == CLK_DIV) begin
                        scl_out <= 1'b1;  // clock high
                    end else if (clk_cnt == CLK_DIV * 2) begin
                        scl_out <= 1'b0;
                        clk_cnt <= 16'd0;
                        if (bit_cnt == 5'd0)
                            state <= S_ACK1;
                        else
                            bit_cnt <= bit_cnt - 5'd1;
                    end
                end

                S_ACK1: begin
                    // Read ACK (release SDA, clock once)
                    clk_cnt <= clk_cnt + 16'd1;
                    if (clk_cnt == 0) begin
                        sda_oe <= 1'b0;  // release SDA for ACK
                    end else if (clk_cnt == CLK_DIV) begin
                        scl_out <= 1'b1;
                    end else if (clk_cnt == CLK_DIV * 2) begin
                        scl_out <= 1'b0;
                        sda_oe  <= 1'b1;
                        clk_cnt <= 16'd0;
                        bit_cnt <= 5'd7;
                        state   <= S_REG_HI;
                    end
                end

                S_REG_HI: begin
                    // Send register address high byte
                    clk_cnt <= clk_cnt + 16'd1;
                    if (clk_cnt == 0) begin
                        sda_out <= shift_reg[23 - (7 - bit_cnt[2:0])];
                        scl_out <= 1'b0;
                    end else if (clk_cnt == CLK_DIV) begin
                        scl_out <= 1'b1;
                    end else if (clk_cnt == CLK_DIV * 2) begin
                        scl_out <= 1'b0;
                        clk_cnt <= 16'd0;
                        if (bit_cnt == 5'd0)
                            state <= S_ACK2;
                        else
                            bit_cnt <= bit_cnt - 5'd1;
                    end
                end

                S_ACK2: begin
                    clk_cnt <= clk_cnt + 16'd1;
                    if (clk_cnt == 0) sda_oe <= 1'b0;
                    else if (clk_cnt == CLK_DIV) scl_out <= 1'b1;
                    else if (clk_cnt == CLK_DIV * 2) begin
                        scl_out <= 1'b0;
                        sda_oe  <= 1'b1;
                        clk_cnt <= 16'd0;
                        bit_cnt <= 5'd7;
                        state   <= S_REG_LO;
                    end
                end

                S_REG_LO: begin
                    // Send register address low byte
                    clk_cnt <= clk_cnt + 16'd1;
                    if (clk_cnt == 0) begin
                        sda_out <= shift_reg[15 - (7 - bit_cnt[2:0])];
                        scl_out <= 1'b0;
                    end else if (clk_cnt == CLK_DIV) begin
                        scl_out <= 1'b1;
                    end else if (clk_cnt == CLK_DIV * 2) begin
                        scl_out <= 1'b0;
                        clk_cnt <= 16'd0;
                        if (bit_cnt == 5'd0)
                            state <= S_ACK3;
                        else
                            bit_cnt <= bit_cnt - 5'd1;
                    end
                end

                S_ACK3: begin
                    clk_cnt <= clk_cnt + 16'd1;
                    if (clk_cnt == 0) sda_oe <= 1'b0;
                    else if (clk_cnt == CLK_DIV) scl_out <= 1'b1;
                    else if (clk_cnt == CLK_DIV * 2) begin
                        scl_out <= 1'b0;
                        sda_oe  <= 1'b1;
                        clk_cnt <= 16'd0;
                        bit_cnt <= 5'd7;
                        state   <= S_DATA;
                    end
                end

                S_DATA: begin
                    // Send data byte
                    clk_cnt <= clk_cnt + 16'd1;
                    if (clk_cnt == 0) begin
                        sda_out <= shift_reg[7 - (7 - bit_cnt[2:0])];
                        scl_out <= 1'b0;
                    end else if (clk_cnt == CLK_DIV) begin
                        scl_out <= 1'b1;
                    end else if (clk_cnt == CLK_DIV * 2) begin
                        scl_out <= 1'b0;
                        clk_cnt <= 16'd0;
                        if (bit_cnt == 5'd0)
                            state <= S_ACK4;
                        else
                            bit_cnt <= bit_cnt - 5'd1;
                    end
                end

                S_ACK4: begin
                    clk_cnt <= clk_cnt + 16'd1;
                    if (clk_cnt == 0) sda_oe <= 1'b0;
                    else if (clk_cnt == CLK_DIV) scl_out <= 1'b1;
                    else if (clk_cnt == CLK_DIV * 2) begin
                        scl_out <= 1'b0;
                        sda_oe  <= 1'b1;
                        clk_cnt <= 16'd0;
                        state   <= S_STOP;
                    end
                end

                S_STOP: begin
                    // I2C stop: SDA rises while SCL high
                    clk_cnt <= clk_cnt + 16'd1;
                    if (clk_cnt == 0) begin
                        sda_out <= 1'b0;
                    end else if (clk_cnt == CLK_DIV) begin
                        scl_out <= 1'b1;
                    end else if (clk_cnt == CLK_DIV * 2) begin
                        sda_out <= 1'b1;  // SDA high = stop
                    end else if (clk_cnt == CLK_DIV * 3) begin
                        clk_cnt <= 16'd0;
                        state   <= S_NEXT;
                    end
                end

                S_NEXT: begin
                    if (reg_idx == NUM_REGS - 1) begin
                        init_done <= 1'b1;
                        state     <= S_DONE;
                    end else begin
                        reg_idx  <= reg_idx + 6'd1;
                        // Add delay after software reset (reg index 1)
                        if (reg_idx == 6'd1) begin
                            wait_cnt <= 20'd0;
                            state    <= S_WAIT;
                        end else begin
                            state <= S_START;
                        end
                    end
                end

                S_DONE: begin
                    // Initialization complete — stay idle
                    sda_oe  <= 1'b0;
                    scl_oe  <= 1'b0;
                    sda_out <= 1'b1;
                    scl_out <= 1'b1;
                end
            endcase
        end
    end

endmodule
