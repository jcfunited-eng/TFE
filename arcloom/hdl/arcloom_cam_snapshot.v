// ============================================================
// ArcLoom Camera Snapshot Buffer
// ============================================================
//
// Captures one Y-channel frame at quarter resolution (80x60)
// to BRAM on trigger. Python reads it out word by word over AXI.
//
// Quarter resolution: skip 3 of 4 Y pixels and 3 of 4 lines.
// Storage: 4,800 bytes = 1,200 x 32-bit words.
// Uses ~38Kb of BRAM (<1% of Zynq-7020's 4.9Mb).
//
// Target: PYNQ-Z2 (XC7Z020-1CLG400C)
// ============================================================

(* DONT_TOUCH = "TRUE" *)
module arcloom_cam_snapshot (
    input  wire        clk,
    input  wire        rst_n,

    // DVP inputs
    input  wire        pclk,
    input  wire        vsync,
    input  wire        href,
    input  wire [7:0]  pixel_data,

    // Control
    input  wire        snapshot_trigger,
    output reg         snapshot_done,
    output reg         snapshot_busy,

    // Read port
    input  wire [10:0] read_addr,         // 0-1199
    output reg  [31:0] read_data
);

    // ---- PCLK synchronization ----
    reg [2:0] pclk_sync, vsync_sync, href_sync;

    always @(posedge clk) begin
        pclk_sync  <= {pclk_sync[1:0], pclk};
        vsync_sync <= {vsync_sync[1:0], vsync};
        href_sync  <= {href_sync[1:0], href};
    end

    wire pclk_rise = pclk_sync[1] & ~pclk_sync[2];
    wire vsync_s   = vsync_sync[2];
    wire href_s    = href_sync[2];

    // pixel_data is read directly in the capture logic below.
    // pclk_rise is already delayed 2 clocks by the synchronizer,
    // so pixel_data is stable when pclk_rise asserts.

    // ---- Frame BRAM ----
    // Simple dual-port: one write port, one read port.
    // 1,200 words x 32 bits = 4,800 bytes = 80x60 Y pixels.
    (* ram_style = "block" *)
    reg [31:0] frame_bram [0:1199];

    // Write port
    reg [10:0] wr_addr;
    reg [31:0] wr_data;
    reg        wr_en;

    always @(posedge clk) begin
        if (wr_en)
            frame_bram[wr_addr] <= wr_data;
    end

    // Read port
    always @(posedge clk) begin
        read_data <= frame_bram[read_addr];
    end

    // ---- Pixel accumulator ----
    reg [31:0] word_acc;
    reg [1:0]  byte_idx;      // 0-3: which byte in word
    reg        byte_toggle;   // YUV422: 0=Y, 1=U/V
    reg [1:0]  px_skip_cnt;   // count to 4: keep 1, skip 3
    reg [1:0]  ln_skip_cnt;   // count to 4: keep 1, skip 3
    reg        active_line;   // this line is being captured
    reg [8:0]  line_num;

    // ---- State machine ----
    reg        prev_vsync;
    reg        prev_href;
    reg        capturing;
    reg        armed;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            prev_vsync    <= 1'b1;
            prev_href     <= 1'b0;
            capturing     <= 1'b0;
            armed         <= 1'b0;
            snapshot_done <= 1'b0;
            snapshot_busy <= 1'b0;
            wr_addr       <= 11'd0;
            wr_data       <= 32'd0;
            wr_en         <= 1'b0;
            word_acc      <= 32'd0;
            byte_idx      <= 2'd0;
            byte_toggle   <= 1'b0;
            px_skip_cnt   <= 2'd0;
            ln_skip_cnt   <= 2'd0;
            active_line   <= 1'b0;
            line_num      <= 9'd0;
        end else begin
            prev_vsync <= vsync_s;
            prev_href  <= href_s;
            wr_en      <= 1'b0;

            // Arm on trigger
            if (snapshot_trigger && !capturing && !armed) begin
                armed         <= 1'b1;
                snapshot_done <= 1'b0;
                snapshot_busy <= 1'b1;
            end

            // Start on VSYNC falling edge
            if (armed && prev_vsync && !vsync_s) begin
                armed       <= 1'b0;
                capturing   <= 1'b1;
                wr_addr     <= 11'd0;
                word_acc    <= 32'd0;
                byte_idx    <= 2'd0;
                byte_toggle <= 1'b0;
                px_skip_cnt <= 2'd0;
                ln_skip_cnt <= 2'd0;
                active_line <= 1'b1;  // first line is active
                line_num    <= 9'd0;
            end

            // End on VSYNC rising edge
            if (capturing && !prev_vsync && vsync_s) begin
                capturing     <= 1'b0;
                snapshot_done <= 1'b1;
                snapshot_busy <= 1'b0;
            end

            // Pixel capture
            if (capturing && pclk_rise && href_s) begin
                if (!byte_toggle && active_line) begin
                    // Y byte on an active line
                    if (px_skip_cnt == 2'd0) begin
                        // Keep this pixel
                        case (byte_idx)
                            2'd0: word_acc[7:0]   <= pixel_data;
                            2'd1: word_acc[15:8]  <= pixel_data;
                            2'd2: word_acc[23:16] <= pixel_data;
                            2'd3: begin
                                // Word complete — write to BRAM
                                wr_data <= {pixel_data, word_acc[23:0]};
                                wr_en   <= (wr_addr < 11'd1200);
                                wr_addr <= wr_addr + 11'd1;
                            end
                        endcase
                        byte_idx <= byte_idx + 2'd1;
                    end
                    px_skip_cnt <= px_skip_cnt + 2'd1;  // wraps 0->1->2->3->0
                end
                byte_toggle <= ~byte_toggle;
            end

            // Line boundary (HREF falling)
            if (capturing && prev_href && !href_s) begin
                byte_toggle <= 1'b0;
                px_skip_cnt <= 2'd0;
                byte_idx    <= 2'd0;
                line_num    <= line_num + 9'd1;
                // Line skip: keep 1 of 4
                ln_skip_cnt <= ln_skip_cnt + 2'd1;
                active_line <= (ln_skip_cnt == 2'd3);  // next line active when counter wraps to 0
            end
        end
    end

endmodule
