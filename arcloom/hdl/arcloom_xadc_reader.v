// ============================================================
// ArcLoom XADC DRP Reader — 3-Channel via EOS + Sequential Read
// ============================================================
//
// Continuous sequence mode on VAUX1, VAUX6, VAUX9.
// After each End-of-Sequence (EOS), reads all 3 status registers
// by their known DRP addresses. No reliance on CHANNEL output.
//
// INIT_40 and INIT_41 are IDENTICAL to proven single-channel.
// Only INIT_48/49 differ (enable 3 channels instead of 1).
//
// PYNQ-Z2 pins:
//   A0 = VAUX1 (E17/D18) — front
//   A1 = VAUX9 (E18/E19) — left
//   A2 = VAUX6 (K14/J14) — right
// ============================================================

module arcloom_xadc_reader (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        vauxp1, vauxn1,  // Front (A0)
    input  wire        vauxp9, vauxn9,  // Left (A1)
    input  wire        vauxp6, vauxn6,  // Right (A2)

    output reg  [15:0] adc_data,
    output reg         adc_valid,
    output reg  [15:0] adc_data_left,
    output reg         adc_valid_left,
    output reg  [15:0] adc_data_right,
    output reg         adc_valid_right,

    output wire [4:0]  channel_out
);

    wire        drdy;
    wire [15:0] do_drp;
    wire [4:0]  channel;
    wire        eoc, eos, busy;

    reg  [6:0]  daddr;
    reg         den, dwe;
    reg  [15:0] di_drp;

    // ---- XADC primitive ----
    // INIT_40 and INIT_41: PROVEN values from single-channel (DO NOT CHANGE)
    // INIT_48/49: enable 3 VAUX channels in sequencer
    XADC #(
        .INIT_40(16'h2111),  // Channel 17, AVG[13:12]=10 = 64-sample averaging, ACQ[8]=1 = 10-cycle base
        .INIT_41(16'h21A0),  // SEQ=0010 = CONTINUOUS SEQUENCE MODE
        .INIT_42(16'h0400),  // DCLK/4

        // Sequence channel enables (UG480 Tables 4-1, 4-2):
        // INIT_48 = on-chip only: bit[0]=calibration. NO VAUX HERE.
        .INIT_48(16'h0001),
        // INIT_49 = VAUX channels: bit[N]=VAUX[N]
        //   bit[1]=VAUX1, bit[6]=VAUX6, bit[9]=VAUX9
        //   0x0002 + 0x0040 + 0x0200 = 0x0242
        .INIT_49(16'h0242),

        .INIT_4C(16'h0000),  // On-chip averaging: none needed
        .INIT_4D(16'h0242),  // VAUX averaging: VAUX1(1), VAUX6(6), VAUX9(9)
        .INIT_4E(16'h0000),  // On-chip acquisition time: default
        .INIT_4F(16'h0242),  // VAUX acquisition time: extended for VAUX1, VAUX6, VAUX9

        .INIT_50(16'hB5ED),
        .INIT_51(16'h5999),
        .INIT_52(16'hA147),
        .INIT_53(16'hDDDD),
        .INIT_54(16'hA93A),
        .INIT_55(16'h5111),
        .INIT_56(16'h91EB),
        .INIT_57(16'hAE4E),
        .INIT_58(16'h0000),
        .INIT_59(16'h0000),
        .INIT_5A(16'h0000),
        .INIT_5B(16'h0000),
        .INIT_5C(16'h0000),
        .INIT_5D(16'h0000),
        .INIT_5E(16'h0000),
        .INIT_5F(16'h0000),

        .SIM_MONITOR_FILE(""),
        .IS_CONVSTCLK_INVERTED(1'b0),
        .IS_DCLK_INVERTED(1'b0)
    ) xadc_inst (
        .DCLK(clk),
        .DEN(den),
        .DADDR(daddr),
        .DWE(dwe),
        .DI(di_drp),
        .DO(do_drp),
        .DRDY(drdy),

        .CHANNEL(channel),
        .EOC(eoc),
        .EOS(eos),
        .BUSY(busy),

        .ALM(), .OT(),
        .JTAGBUSY(), .JTAGLOCKED(), .JTAGMODIFIED(),

        .VP(1'b0), .VN(1'b0),

        // VAUXP[15:0]: bit[1]=VAUX1, bit[6]=VAUX6, bit[9]=VAUX9
        .VAUXP({6'b0, vauxp9, 2'b0, vauxp6, 4'b0, vauxp1, 1'b0}),
        .VAUXN({6'b0, vauxn9, 2'b0, vauxn6, 4'b0, vauxn1, 1'b0}),

        .CONVST(1'b0),
        .CONVSTCLK(1'b0),
        .RESET(~rst_n),
        .MUXADDR()
    );

    // ---- Spike rejection ----
    // If a reading jumps more than SPIKE_THRESH (in raw 16-bit XADC units)
    // from the previous accepted reading, reject it and hold previous value.
    // XADC returns 16-bit left-justified: [15:4] = 12-bit ADC value.
    // 150 ADC counts = 150 << 4 = 2400 raw units.
    localparam [15:0] SPIKE_THRESH = 16'd2400;

    reg [15:0] prev_front, prev_left, prev_right;
    reg        has_prev_front, has_prev_left, has_prev_right;
    reg [1:0]  reject_cnt_front, reject_cnt_left, reject_cnt_right;

    function spike_ok_front;
        input [15:0] new_val;
        begin
            spike_ok_front = (new_val > prev_front) ?
                             (new_val - prev_front <= SPIKE_THRESH) :
                             (prev_front - new_val <= SPIKE_THRESH);
        end
    endfunction

    function spike_ok_right;
        input [15:0] new_val;
        begin
            spike_ok_right = (new_val > prev_right) ?
                             (new_val - prev_right <= SPIKE_THRESH) :
                             (prev_right - new_val <= SPIKE_THRESH);
        end
    endfunction

    function spike_ok_left;
        input [15:0] new_val;
        begin
            spike_ok_left = (new_val > prev_left) ?
                            (new_val - prev_left <= SPIKE_THRESH) :
                            (prev_left - new_val <= SPIKE_THRESH);
        end
    endfunction

    // ---- State machine: read all 3 registers after EOS ----
    // Status register DRP addresses:
    //   VAUX1 = 0x11, VAUX6 = 0x16, VAUX9 = 0x19

    localparam [2:0] IDLE       = 3'd0;
    localparam [2:0] RD_FRONT   = 3'd1;
    localparam [2:0] WAIT_FRONT = 3'd2;
    localparam [2:0] RD_RIGHT   = 3'd3;
    localparam [2:0] WAIT_RIGHT = 3'd4;
    localparam [2:0] RD_LEFT    = 3'd5;
    localparam [2:0] WAIT_LEFT  = 3'd6;

    reg [2:0] state;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state           <= IDLE;
            den             <= 1'b0;
            dwe             <= 1'b0;
            daddr           <= 7'h00;
            di_drp          <= 16'h0000;
            adc_data        <= 16'd0;
            adc_valid       <= 1'b0;
            adc_data_left   <= 16'd0;
            adc_valid_left  <= 1'b0;
            adc_data_right  <= 16'd0;
            adc_valid_right <= 1'b0;
            prev_front      <= 16'd0;
            prev_left       <= 16'd0;
            prev_right      <= 16'd0;
            has_prev_front  <= 1'b0;
            has_prev_left   <= 1'b0;
            has_prev_right  <= 1'b0;
            reject_cnt_front <= 2'd0;
            reject_cnt_left  <= 2'd0;
            reject_cnt_right <= 2'd0;
        end else begin
            adc_valid       <= 1'b0;
            adc_valid_left  <= 1'b0;
            adc_valid_right <= 1'b0;
            den             <= 1'b0;

            case (state)
                IDLE: begin
                    // Wait for end-of-sequence: all channels converted
                    if (eos) begin
                        state <= RD_FRONT;
                    end
                end

                // ---- Read front sensor (VAUX1 = 0x11) ----
                RD_FRONT: begin
                    daddr <= 7'h11;
                    den   <= 1'b1;
                    dwe   <= 1'b0;
                    state <= WAIT_FRONT;
                end

                WAIT_FRONT: begin
                    if (drdy) begin
                        if (!has_prev_front || spike_ok_front(do_drp) || reject_cnt_front == 2'd3) begin
                            adc_data  <= do_drp;
                            adc_valid <= 1'b1;
                            prev_front <= do_drp;
                            has_prev_front <= 1'b1;
                            reject_cnt_front <= 2'd0;
                        end else begin
                            reject_cnt_front <= reject_cnt_front + 2'd1;
                        end
                        state <= RD_RIGHT;
                    end
                end

                // ---- Read right sensor (VAUX6 = 0x16) ----
                RD_RIGHT: begin
                    daddr <= 7'h16;
                    den   <= 1'b1;
                    dwe   <= 1'b0;
                    state <= WAIT_RIGHT;
                end

                WAIT_RIGHT: begin
                    if (drdy) begin
                        if (!has_prev_right || spike_ok_right(do_drp) || reject_cnt_right == 2'd3) begin
                            adc_data_right  <= do_drp;
                            adc_valid_right <= 1'b1;
                            prev_right <= do_drp;
                            has_prev_right <= 1'b1;
                            reject_cnt_right <= 2'd0;
                        end else begin
                            reject_cnt_right <= reject_cnt_right + 2'd1;
                        end
                        state <= RD_LEFT;
                    end
                end

                // ---- Read left sensor (VAUX9 = 0x19) ----
                RD_LEFT: begin
                    daddr <= 7'h19;
                    den   <= 1'b1;
                    dwe   <= 1'b0;
                    state <= WAIT_LEFT;
                end

                WAIT_LEFT: begin
                    if (drdy) begin
                        if (!has_prev_left || spike_ok_left(do_drp) || reject_cnt_left == 2'd3) begin
                            adc_data_left  <= do_drp;
                            adc_valid_left <= 1'b1;
                            prev_left <= do_drp;
                            has_prev_left <= 1'b1;
                            reject_cnt_left <= 2'd0;
                        end else begin
                            reject_cnt_left <= reject_cnt_left + 2'd1;
                        end
                        state <= IDLE;
                    end
                end

                default: state <= IDLE;
            endcase
        end
    end

    assign channel_out = channel;

endmodule
