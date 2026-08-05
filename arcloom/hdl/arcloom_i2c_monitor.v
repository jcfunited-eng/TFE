// ============================================================
// ArcLoom I2C Bus Monitor — Passive Transaction Logger
// ============================================================
//
// Watches SCL/SDA lines and captures every I2C transaction to
// a ring buffer in BRAM. Python reads the buffer to see exactly
// what's happening on the bus — address, register, data, ACK/NAK.
//
// PASSIVE — does not drive SCL or SDA. Only observes.
//
// Ring buffer: 1024 entries × 32 bits. Each entry captures one
// complete byte + ACK from the bus:
//   [31:24] = sequence number (wraps at 255)
//   [23:16] = byte value (8 bits from bus)
//   [15:8]  = transaction byte position (0=addr, 1=reg_hi, 2=reg_lo, 3=data)
//   [7]     = ACK bit (0=ACK, 1=NAK)
//   [6]     = START detected
//   [5]     = STOP detected
//   [4:0]   = reserved
//
// Target: PYNQ-Z2 (XC7Z020-1CLG400C)
// ============================================================

module arcloom_i2c_monitor (
    input  wire        clk,        // system clock (100MHz)
    input  wire        rst_n,

    // I2C bus (directly from pins — passive observe only)
    input  wire        scl_in,
    input  wire        sda_in,

    // Ring buffer read port (from AXI)
    input  wire [9:0]  read_addr,   // 0-1023
    output reg  [31:0] read_data,

    // Status
    output reg  [9:0]  write_count, // total entries written (wraps)
    output reg         overflow     // buffer has wrapped at least once
);

    // ---- Synchronize bus signals ----
    reg [2:0] scl_sync, sda_sync;

    always @(posedge clk) begin
        scl_sync <= {scl_sync[1:0], scl_in};
        sda_sync <= {sda_sync[1:0], sda_in};
    end

    wire scl = scl_sync[2];
    wire sda = sda_sync[2];
    wire scl_prev = scl_sync[2];  // need previous for edge detection
    reg  scl_d, sda_d;

    always @(posedge clk) begin
        scl_d <= scl;
        sda_d <= sda;
    end

    wire scl_rise = scl & ~scl_d;
    wire scl_fall = ~scl & scl_d;
    // START: SDA falls while SCL is high
    wire start_det = ~sda & sda_d & scl;
    // STOP: SDA rises while SCL is high
    wire stop_det = sda & ~sda_d & scl;

    // ---- Ring buffer BRAM ----
    (* ram_style = "block" *)
    reg [31:0] ring_buf [0:1023];
    reg [9:0]  wr_ptr;

    // Read port
    always @(posedge clk) begin
        read_data <= ring_buf[read_addr];
    end

    // ---- Byte capture state machine ----
    reg [7:0]  shift_reg;     // incoming bits
    reg [3:0]  bit_count;     // 0-8 (8 = ACK bit)
    reg [7:0]  seq_num;       // sequence counter
    reg [7:0]  byte_pos;      // position in transaction (0=addr, 1=reg_hi, etc.)
    reg        in_transaction;
    reg        ack_bit;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_ptr         <= 10'd0;
            write_count    <= 10'd0;
            overflow       <= 1'b0;
            shift_reg      <= 8'd0;
            bit_count      <= 4'd0;
            seq_num        <= 8'd0;
            byte_pos       <= 8'd0;
            in_transaction <= 1'b0;
            ack_bit        <= 1'b1;
        end else begin

            // START condition
            if (start_det) begin
                in_transaction <= 1'b1;
                bit_count      <= 4'd0;
                byte_pos       <= 8'd0;
                shift_reg      <= 8'd0;

                // Log START event
                ring_buf[wr_ptr] <= {seq_num, 8'h00, 8'h00, 1'b1, 1'b1, 1'b0, 5'd0};
                wr_ptr    <= wr_ptr + 10'd1;
                seq_num   <= seq_num + 8'd1;
                if (wr_ptr == 10'd1023)
                    overflow <= 1'b1;
                write_count <= write_count + 10'd1;
            end

            // STOP condition
            if (stop_det) begin
                in_transaction <= 1'b0;

                // Log STOP event
                ring_buf[wr_ptr] <= {seq_num, 8'h00, 8'h00, 1'b0, 1'b0, 1'b1, 5'd0};
                wr_ptr    <= wr_ptr + 10'd1;
                seq_num   <= seq_num + 8'd1;
                if (wr_ptr == 10'd1023)
                    overflow <= 1'b1;
                write_count <= write_count + 10'd1;
            end

            // Data sampling on SCL rising edge
            if (scl_rise && in_transaction && !start_det && !stop_det) begin
                if (bit_count < 4'd8) begin
                    // Data bit — shift in MSB first
                    shift_reg <= {shift_reg[6:0], sda};
                    bit_count <= bit_count + 4'd1;
                end else begin
                    // ACK/NAK bit (9th clock)
                    ack_bit   <= sda;  // 0=ACK, 1=NAK

                    // Log complete byte + ACK
                    ring_buf[wr_ptr] <= {seq_num, shift_reg, byte_pos,
                                         sda, 1'b0, 1'b0, 5'd0};
                    wr_ptr    <= wr_ptr + 10'd1;
                    seq_num   <= seq_num + 8'd1;
                    if (wr_ptr == 10'd1023)
                        overflow <= 1'b1;
                    write_count <= write_count + 10'd1;

                    // Reset for next byte
                    bit_count <= 4'd0;
                    byte_pos  <= byte_pos + 8'd1;
                    shift_reg <= 8'd0;
                end
            end
        end
    end

endmodule
