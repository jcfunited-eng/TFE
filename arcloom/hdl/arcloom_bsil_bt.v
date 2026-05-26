// ============================================================
// ArcLoom BSIL-BT — Binary to Balanced Ternary Sensor Encoder
// ============================================================
//
// BRAM-based lookup table for BT conversion. The 12-bit ADC
// value (after baseline subtraction) indexes a ROM containing
// pre-computed 8-trit balanced ternary encodings.
//
// Uses 1 BRAM per instance (4096 × 16 bits = 8KB = 1 BRAM18).
// Zero LUTs for the conversion itself.
//
// Also computes direction (first derivative) and acceleration
// (second derivative) via the same ROM. The derivatives use
// the delta value as an index into the same BT table.
//
// Trit encoding: 00=null(0), 01=+1, 10=-1, 11=invalid
// ============================================================

module arcloom_bsil_bt #(
    parameter N_TRITS = 8,
    parameter BASELINE = 12'd80       // default, overridden by baseline_in if nonzero
)(
    input  wire        clk,
    input  wire        rst_n,

    input  wire [11:0] adc_value,
    input  wire        adc_valid,
    input  wire [11:0] baseline_in,   // runtime baseline from AXI (0 = use parameter)

    output reg  [2*N_TRITS-1:0] bt_distance,
    output reg  [2*N_TRITS-1:0] bt_direction,
    output reg  [2*N_TRITS-1:0] bt_acceleration,
    output reg  out_valid
);

    // ================================================================
    // BRAM ROM: pre-computed balanced ternary for values 0-4095
    // Initialized at synthesis time. 1 BRAM18 per instance.
    // ================================================================
    reg [15:0] bt_rom [0:4095];

    // Pre-compute ROM contents at elaboration time
    integer ii, jj;
    reg [15:0] rom_val;
    reg signed [15:0] working;
    reg [1:0] digit;
    reg neg_flag;

    initial begin
        for (ii = 0; ii < 4096; ii = ii + 1) begin
            rom_val = 16'd0;
            working = ii;
            neg_flag = 0;

            if (working < 0) begin
                working = -working;
                neg_flag = 1;
            end

            for (jj = 0; jj < N_TRITS; jj = jj + 1) begin
                case (working % 3)
                    0: begin digit = 2'b00; working = working / 3; end
                    1: begin digit = 2'b01; working = (working - 1) / 3; end
                    2: begin digit = 2'b10; working = (working + 1) / 3; end
                    default: begin digit = 2'b00; working = working / 3; end
                endcase
                rom_val[2*jj +: 2] = digit;
            end

            if (neg_flag) begin
                for (jj = 0; jj < N_TRITS; jj = jj + 1) begin
                    case (rom_val[2*jj +: 2])
                        2'b01: rom_val[2*jj +: 2] = 2'b10;
                        2'b10: rom_val[2*jj +: 2] = 2'b01;
                        default: ;
                    endcase
                end
            end

            bt_rom[ii] = rom_val;
        end
    end

    // ================================================================
    // Address computation (combinational)
    // ================================================================
    // Runtime baseline: use baseline_in if nonzero, else parameter default
    wire [11:0] active_baseline = (baseline_in != 12'd0) ? baseline_in : BASELINE;

    // Centered value: subtract baseline so "nothing" ≈ 0
    // Clamp to 3280 max — 8-trit BT range is ±3280.
    // Values above 3280 overflow the encoding and INVERT the sign.
    wire [11:0] centered_raw = (adc_value > active_baseline) ?
                                (adc_value - active_baseline) : 12'd0;
    wire [11:0] centered = (centered_raw > 12'd3280) ? 12'd3280 : centered_raw;

    // ================================================================
    // History for derivatives
    // ================================================================
    reg [11:0] prev_adc, prev_prev_adc;
    reg        has_prev;

    // Delta (unsigned magnitude, direction tracked by sign)
    wire [11:0] delta_mag = (adc_value > prev_adc) ?
                             (adc_value - prev_adc) :
                             (prev_adc - adc_value);
    wire        delta_neg = (adc_value < prev_adc);

    // Acceleration magnitude
    wire signed [13:0] accel_signed = ({2'b0, adc_value})
                                    - ({1'b0, prev_adc, 1'b0})
                                    + ({2'b0, prev_prev_adc});
    wire [11:0] accel_mag = accel_signed[13] ?
                            (~accel_signed[11:0] + 12'd1) :
                            accel_signed[11:0];
    wire        accel_neg = accel_signed[13];

    // ================================================================
    // ROM read + output registration (CLOCKED)
    // ================================================================
    // ROM reads are registered (1 cycle latency) — standard BRAM inference
    reg [15:0] rom_dist, rom_delta, rom_accel;

    always @(posedge clk) begin
        rom_dist  <= bt_rom[centered];
        rom_delta <= bt_rom[delta_mag];
        rom_accel <= bt_rom[accel_mag];
    end

    // Negate ROM output for negative deltas/accelerations
    function [15:0] negate_bt;
        input [15:0] val;
        integer k;
        begin
            negate_bt = val;
            for (k = 0; k < N_TRITS; k = k + 1) begin
                case (val[2*k +: 2])
                    2'b01: negate_bt[2*k +: 2] = 2'b10;
                    2'b10: negate_bt[2*k +: 2] = 2'b01;
                    default: ;
                endcase
            end
        end
    endfunction

    // Pipeline: valid delayed by 2 cycles (ROM read + output reg)
    reg valid_d1, valid_d2;
    reg delta_neg_d1, accel_neg_d1;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            bt_distance     <= {2*N_TRITS{1'b0}};
            bt_direction    <= {2*N_TRITS{1'b0}};
            bt_acceleration <= {2*N_TRITS{1'b0}};
            out_valid       <= 1'b0;
            prev_adc        <= 12'd0;
            prev_prev_adc   <= 12'd0;
            has_prev        <= 1'b0;
            valid_d1        <= 1'b0;
            valid_d2        <= 1'b0;
            delta_neg_d1    <= 1'b0;
            accel_neg_d1    <= 1'b0;
        end else begin
            // Pipeline stage 1: ROM address captured
            valid_d1     <= adc_valid;
            delta_neg_d1 <= delta_neg;
            accel_neg_d1 <= accel_neg;

            // Pipeline stage 2: ROM data ready, output
            valid_d2  <= valid_d1;
            out_valid <= valid_d2;

            if (valid_d2) begin
                bt_distance     <= rom_dist;
                bt_direction    <= has_prev ? (delta_neg_d1 ? negate_bt(rom_delta) : rom_delta)
                                           : {2*N_TRITS{1'b0}};
                bt_acceleration <= has_prev ? (accel_neg_d1 ? negate_bt(rom_accel) : rom_accel)
                                           : {2*N_TRITS{1'b0}};
            end

            // Update history on valid input
            if (adc_valid) begin
                prev_prev_adc <= prev_adc;
                prev_adc      <= adc_value;
                has_prev      <= 1'b1;
            end
        end
    end

endmodule
