// ============================================================
// ArcLoom XADC DRP Reader — 3-Channel Analog Input
// ============================================================
//
// Reads 3 XADC auxiliary channels for front/left/right sensors:
//   VAUX1 (A0, E17/D18) — Front sensor
//   VAUX9 (A1, E18/E19) — Left sensor
//   VAUX6 (A2, K14/J14) — Right sensor
//
// Source: PYNQ-Z2 master XDC pin mappings
//
// NO ARM involvement. NO AXI. Pure PL hardware path.
//
// Output: 3 x 12-bit ADC values + valid pulse per channel
//
// Target: PYNQ-Z2 (XC7Z020-1CLG400C)
// ============================================================

module arcloom_xadc_reader (
    input  wire        clk,
    input  wire        rst_n,

    // Analog inputs — 3 channels
    input  wire        vauxp1,     // VAUX1 (A0, front)
    input  wire        vauxn1,
    input  wire        vauxp9,     // VAUX9 (A1, left)
    input  wire        vauxn9,
    input  wire        vauxp6,     // VAUX6 (A2, right)
    input  wire        vauxn6,

    // ADC outputs — 3 channels, 16-bit aligned (data in [15:4])
    output reg  [15:0] adc_data,       // front (VAUX1) — primary output
    output reg         adc_valid,
    output reg  [15:0] adc_data_left,  // left (VAUX9)
    output reg         adc_valid_left,
    output reg  [15:0] adc_data_right, // right (VAUX6)
    output reg         adc_valid_right,

    // Debug
    output wire [4:0]  channel_out
);

    // ---- XADC DRP interface wires ----
    wire        drdy;
    wire [15:0] do_drp;
    wire [4:0]  channel;
    wire        eoc;
    wire        eos;
    wire        busy;

    reg  [6:0]  daddr;
    reg         den;
    reg         dwe;
    reg  [15:0] di_drp;

    // ---- XADC primitive ----
    // Sequence mode: cycle through VAUX1, VAUX6, VAUX9
    XADC #(
        // INIT_40: Config reg 0
        //   [12] = 0: not in sequence mode for single channel
        //   Use sequence mode via INIT_41
        .INIT_40(16'h0000),  // Config reg 0: default (sequence mode controls channel)

        // INIT_41: Config reg 1
        //   [15:12] = 0011: continuous sequence mode
        .INIT_41(16'h31A0),  // Continuous sequence, no alarms

        // INIT_42: Config reg 2
        .INIT_42(16'h0400),  // DCLK/4

        // INIT_48: Sequence register — enable VAUX channels 0-7
        //   Bit 1 = VAUX1 (A0, front)
        //   Bit 6 = VAUX6 (A2, right)
        .INIT_48(16'h0042),  // Enable VAUX1 + VAUX6

        // INIT_49: Sequence register — enable VAUX channels 8-15
        //   Bit 1 = VAUX9 (A1, left)
        .INIT_49(16'h0002),  // Enable VAUX9

        // Averaging
        .INIT_4C(16'h0000),
        .INIT_4D(16'h0000),

        // Analog input mode (unipolar)
        .INIT_4E(16'h0000),
        .INIT_4F(16'h0000),

        // Alarm thresholds (disabled)
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

        .ALM(),
        .OT(),

        .JTAGBUSY(),
        .JTAGLOCKED(),
        .JTAGMODIFIED(),

        .VP(1'b0),
        .VN(1'b0),

        // VAUXP/N are 16-bit vectors: bit[N] = VAUX channel N
        // We connect VAUX1, VAUX6, VAUX9
        .VAUXP({6'b0, vauxp9, 2'b0, vauxp6, 4'b0, vauxp1, 1'b0}),
        .VAUXN({6'b0, vauxn9, 2'b0, vauxn6, 4'b0, vauxn1, 1'b0}),

        .CONVST(1'b0),
        .CONVSTCLK(1'b0),
        .RESET(~rst_n),
        .MUXADDR()
    );

    // ---- DRP read state machine ----
    // On each EOC, read the channel that just converted.
    // The CHANNEL output tells us which one completed.

    localparam VAUX1_ADDR = 7'h11;  // Front (A0)
    localparam VAUX9_ADDR = 7'h19;  // Left (A1)
    localparam VAUX6_ADDR = 7'h16;  // Right (A2)

    reg [1:0] state;
    localparam IDLE = 2'd0;
    localparam WAIT = 2'd1;

    reg [4:0] read_channel;  // which channel we're reading

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
            read_channel    <= 5'd0;
        end else begin
            adc_valid       <= 1'b0;
            adc_valid_left  <= 1'b0;
            adc_valid_right <= 1'b0;
            den             <= 1'b0;

            case (state)
                IDLE: begin
                    if (eoc) begin
                        // Read the channel that just finished
                        read_channel <= channel;
                        case (channel)
                            5'h01: daddr <= VAUX1_ADDR;  // VAUX1 = front
                            5'h09: daddr <= VAUX9_ADDR;  // VAUX9 = left
                            5'h06: daddr <= VAUX6_ADDR;  // VAUX6 = right
                            default: daddr <= {2'b0, channel};
                        endcase
                        den   <= 1'b1;
                        dwe   <= 1'b0;
                        state <= WAIT;
                    end
                end

                WAIT: begin
                    if (drdy) begin
                        case (read_channel)
                            5'h01: begin
                                adc_data  <= do_drp;
                                adc_valid <= 1'b1;
                            end
                            5'h09: begin
                                adc_data_left  <= do_drp;
                                adc_valid_left <= 1'b1;
                            end
                            5'h06: begin
                                adc_data_right  <= do_drp;
                                adc_valid_right <= 1'b1;
                            end
                        endcase
                        state <= IDLE;
                    end
                end

                default: state <= IDLE;
            endcase
        end
    end

    assign channel_out = channel;

endmodule
