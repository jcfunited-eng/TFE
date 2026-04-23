// ============================================================
// ArcLoom XADC DRP Reader — Direct PL Analog Input
// ============================================================
//
// Reads XADC auxiliary channel VAUX1 (Arduino A0 on PYNQ-Z2)
// directly through the Dynamic Reconfiguration Port (DRP).
//
// NO ARM involvement. NO AXI. Pure PL hardware path.
//
// The XADC is instantiated directly in the PL fabric using
// the XADC primitive (XADC #(...) in Zynq-7000).
//
// Arduino A0 → PCB resistor divider → XADC VAUX1 (AD1P=E17/AD1N=D18)
// → DRP read → 12-bit ADC value → BSIL → SPPU
//
// CRITICAL: Arduino A0 = VAUX1 (AD1), NOT VAUX3 (AD3).
// Source: PYNQ-Z2 master XDC: ar_an0_p=E17 IO_L3P_T0_DQS_AD1P_35
//
// Sampling: continuous, free-running at ~1 MSPS (XADC default)
// Output: 12-bit ADC value + valid pulse on each conversion
//
// Target: PYNQ-Z2 (XC7Z020-1CLG400C)
// ============================================================

module arcloom_xadc_reader (
    input  wire        clk,        // system clock (50-100 MHz)
    input  wire        rst_n,

    // ADC output — 16-bit aligned (data in [15:4], matches XADC DRP format)
    output reg  [15:0] adc_data,   // 16-bit: ADC result in [15:4], [3:0]=0
    output reg         adc_valid,  // pulse: new data available

    // Debug
    output wire [4:0]  channel_out // which channel was just converted
);

    // ---- XADC DRP interface wires ----
    wire        drdy;          // data ready (conversion complete)
    wire [15:0] do_drp;        // data output (16-bit, ADC data in [15:4])
    wire [4:0]  channel;       // channel being converted
    wire        eoc;           // end of conversion
    wire        eos;           // end of sequence
    wire        busy;          // XADC busy

    reg  [6:0]  daddr;         // DRP address
    reg         den;           // DRP enable (read strobe)
    reg         dwe;           // DRP write enable (always 0 for reads)
    reg  [15:0] di_drp;        // DRP data input (unused for reads)

    // ---- XADC primitive instantiation ----
    // Configure for single-channel continuous sampling of VAUX3
    XADC #(
        // Init registers configure the XADC behavior
        // INIT_40: Configuration Register 0
        //   [4:0]  = 10011: CH = 0x13 = VAUX3
        //   [5]    = 0: no extended acquisition
        //   [6]    = 0: no external MUX
        //   [8]    = 0: continuous (not event-driven)
        //   [9]    = 0: unipolar
        //   [11:10]= 00: no averaging
        .INIT_40(16'h0011),  // Config reg 0: VAUX1 (channel 0x11) — Arduino A0 = AD1, NOT AD3

        // INIT_41: Configuration Register 1
        //   [15:12] = 0011: continuous sequence mode
        //   [11]    = 0: no event mode
        //   [3:0]   = 0000: calibration
        .INIT_41(16'h31A0),  // Config reg 1: continuous, no alarms

        // INIT_42: Configuration Register 2
        //   [15:8]  = clock division (DCLK / (2 * DIV))
        //   [5:4]   = power down bits
        .INIT_42(16'h0400),  // Config reg 2: DCLK/4

        // INIT_48: Sequence register - enable VAUX3 in sequence
        //   Bit 1 = VAUX1 enable (Arduino A0 = AD1P/AD1N on PYNQ-Z2)
        .INIT_48(16'h0002),  // Enable VAUX1 in channel sequencer

        // INIT_49: Sequence register for VAUX8-15
        .INIT_49(16'h0000),

        // INIT_4C: Averaging for sequencer channels
        .INIT_4C(16'h0000),  // No averaging

        // INIT_4D: Averaging for aux channels 8-15
        .INIT_4D(16'h0000),

        // INIT_4E: Analog input mode (unipolar/bipolar) for seq channels
        .INIT_4E(16'h0000),  // Unipolar for all

        // INIT_4F: Analog input mode for aux 8-15
        .INIT_4F(16'h0000),

        // INIT_50-5F: Alarm thresholds (disabled)
        .INIT_50(16'hB5ED),  // Temperature upper alarm
        .INIT_51(16'h5999),  // Vccint upper alarm
        .INIT_52(16'hA147),  // Vccaux upper alarm
        .INIT_53(16'hDDDD),  // OT alarm
        .INIT_54(16'hA93A),  // Temperature lower alarm
        .INIT_55(16'h5111),  // Vccint lower alarm
        .INIT_56(16'h91EB),  // Vccaux lower alarm
        .INIT_57(16'hAE4E),  // OT reset
        .INIT_58(16'h0000),
        .INIT_59(16'h0000),
        .INIT_5A(16'h0000),
        .INIT_5B(16'h0000),
        .INIT_5C(16'h0000),
        .INIT_5D(16'h0000),
        .INIT_5E(16'h0000),
        .INIT_5F(16'h0000),

        // Simulation attributes
        .SIM_MONITOR_FILE(""),
        .IS_CONVSTCLK_INVERTED(1'b0),
        .IS_DCLK_INVERTED(1'b0)
    ) xadc_inst (
        // DRP interface
        .DCLK(clk),
        .DEN(den),
        .DADDR(daddr),
        .DWE(dwe),
        .DI(di_drp),
        .DO(do_drp),
        .DRDY(drdy),

        // Status
        .CHANNEL(channel),
        .EOC(eoc),
        .EOS(eos),
        .BUSY(busy),

        // Alarm outputs (active low, directly drive LEDs)
        .ALM(),
        .OT(),

        // JTAG interface (active high reset, active high disable)
        .JTAGBUSY(),
        .JTAGLOCKED(),
        .JTAGMODIFIED(),

        // Dedicated analog input (VP/VN — not used, we use VAUX)
        .VP(1'b0),
        .VN(1'b0),

        // Auxiliary analog inputs
        // On Zynq-7000, VAUX pins are hardwired in silicon to the XADC.
        // No PL routing needed — tie to 0, physical connection exists.
        // INIT_40 selects VAUX3 channel, INIT_48 enables it.
        .VAUXP(16'b0),
        .VAUXN(16'b0),

        // Conversion control
        .CONVST(1'b0),
        .CONVSTCLK(1'b0),
        .RESET(~rst_n),
        .MUXADDR()
    );

    // ---- DRP read state machine ----
    // When EOC fires, read the status register for VAUX3
    // VAUX3 status register DRP address = 7'h13

    localparam VAUX1_ADDR = 7'h11;  // DRP address for VAUX1 status register

    reg [1:0] state;
    localparam IDLE = 2'd0;
    localparam READ = 2'd1;
    localparam WAIT = 2'd2;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state     <= IDLE;
            den       <= 1'b0;
            dwe       <= 1'b0;
            daddr     <= 7'h00;
            di_drp    <= 16'h0000;
            adc_data  <= 16'd0;
            adc_valid <= 1'b0;
        end else begin
            adc_valid <= 1'b0;
            den       <= 1'b0;

            case (state)
                IDLE: begin
                    if (eoc) begin
                        // End of conversion — read VAUX1 result
                        daddr <= VAUX1_ADDR;
                        den   <= 1'b1;
                        dwe   <= 1'b0;
                        state <= WAIT;
                    end
                end

                WAIT: begin
                    if (drdy) begin
                        // Data ready — pass full 16-bit DRP word
                        // ADC value lives in [15:4], [3:0] are sub-LSB
                        adc_data  <= do_drp;
                        adc_valid <= 1'b1;
                        state     <= IDLE;
                    end
                end

                default: state <= IDLE;
            endcase
        end
    end

    assign channel_out = channel;

endmodule
