// ============================================================
// ArcLoom DVP Camera Capture — OV5640 Parallel Interface
// ============================================================
//
// Captures pixel data from OV5640 via 8-bit DVP parallel bus.
//
// OV5640 DVP signals (active during frame):
//   VSYNC: high between frames, low during active frame
//   HREF:  high during active pixels on a line
//   PCLK:  pixel clock — data valid on rising edge
//   D[7:0]: 8-bit pixel data
//
// OV5640 default output format: YUV422 (YUYV)
//   Byte 0: Y0 (luminance of pixel 0)
//   Byte 1: U  (chrominance)
//   Byte 2: Y1 (luminance of pixel 1)
//   Byte 3: V  (chrominance)
//
// For ArcLoom vision: we extract luminance (Y) from every other
// byte, plus accumulate RGB statistics per scanline for color
// discrimination. The kernel processes scanline-level features,
// not individual pixels.
//
// Output: per-scanline statistics updated once per line
//   - mean luminance (8-bit)
//   - edge count (boundary transitions)
//   - luminance range (max - min)
//   - color info from U/V channels
//
// Frame size: configured via I2C to QVGA (320x240) for speed.
// At 25MHz PCLK, QVGA = 320*240*2 bytes = 153,600 bytes/frame
// = ~6ms per frame = ~160 fps. We downsample to ~10 fps.
//
// Target: PYNQ-Z2 (XC7Z020-1CLG400C)
// ============================================================

(* DONT_TOUCH = "TRUE" *)
module arcloom_cam_dvp (
    input  wire        clk,        // system clock (100MHz)
    input  wire        rst_n,

    // DVP inputs from camera
    input  wire        pclk,       // pixel clock from camera (AR12)
    input  wire        vsync,      // vertical sync (AR10)
    input  wire        href,       // horizontal reference (AR11)
    input  wire [7:0]  pixel_data, // D2-D9 (AR2-AR9)

    // Scanline feature outputs (updated once per line)
    output reg  [7:0]  line_y_mean,    // mean luminance
    output reg  [7:0]  line_y_min,     // min luminance
    output reg  [7:0]  line_y_max,     // max luminance
    output reg  [7:0]  line_edge_count,// boundary transitions
    output reg  [7:0]  line_u_mean,    // mean U chrominance
    output reg  [7:0]  line_v_mean,    // mean V chrominance
    output reg  [8:0]  line_number,    // which scanline (0-239)
    output reg         line_valid,     // pulse: new line data ready

    // Frame status
    output reg         frame_active,   // high during active frame
    output reg  [7:0]  frame_count     // frame counter (wraps at 255)
);

    // ---- PCLK domain synchronization ----
    // Synchronize DVP signals to system clock
    reg [2:0] pclk_sync, vsync_sync, href_sync;
    reg [7:0] pixel_sync;

    always @(posedge clk) begin
        pclk_sync  <= {pclk_sync[1:0], pclk};
        vsync_sync <= {vsync_sync[1:0], vsync};
        href_sync  <= {href_sync[1:0], href};
    end

    wire pclk_rise = pclk_sync[1] & ~pclk_sync[2];
    wire vsync_s   = vsync_sync[2];
    wire href_s    = href_sync[2];

    // Latch pixel data on PCLK rising edge
    always @(posedge clk) begin
        if (pclk_rise)
            pixel_sync <= pixel_data;
    end

    // ---- Frame and line tracking ----
    reg        prev_vsync;
    reg        prev_href;
    reg        in_frame;
    reg [8:0]  cur_line;

    // ---- Per-line accumulators ----
    reg [19:0] y_sum;       // sum of Y values (up to 320 * 255 = 81,600)
    reg [7:0]  y_min_acc;
    reg [7:0]  y_max_acc;
    reg [7:0]  y_prev;      // previous Y for edge detection
    reg [7:0]  edge_cnt;
    reg [19:0] u_sum;
    reg [19:0] v_sum;
    reg [9:0]  pixel_count; // pixels in current line
    reg        byte_toggle; // alternates: 0=Y, 1=U/V

    // Edge detection threshold (luminance change > 16 = boundary)
    localparam EDGE_THRESH = 8'd16;

    // Mean approximation: 320 Y pixels/line, so mean = y_sum/320
    // Approximate as y_sum*3/1024 (~6% underread, fine for loom)
    wire [20:0] y_sum_x3 = {1'b0, y_sum} + {y_sum, 1'b0};
    wire [20:0] u_sum_x3 = {1'b0, u_sum} + {u_sum, 1'b0};
    wire [20:0] v_sum_x3 = {1'b0, v_sum} + {v_sum, 1'b0};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            prev_vsync   <= 1'b1;
            prev_href    <= 1'b0;
            in_frame     <= 1'b0;
            cur_line     <= 9'd0;
            y_sum        <= 20'd0;
            y_min_acc    <= 8'hFF;
            y_max_acc    <= 8'h00;
            y_prev       <= 8'd128;
            edge_cnt     <= 8'd0;
            u_sum        <= 20'd0;
            v_sum        <= 20'd0;
            pixel_count  <= 10'd0;
            byte_toggle  <= 1'b0;
            line_valid   <= 1'b0;
            frame_active <= 1'b0;
            frame_count  <= 8'd0;
            line_y_mean  <= 8'd0;
            line_y_min   <= 8'hFF;
            line_y_max   <= 8'h00;
            line_edge_count <= 8'd0;
            line_u_mean  <= 8'd128;
            line_v_mean  <= 8'd128;
            line_number  <= 9'd0;
        end else begin
            line_valid <= 1'b0;
            prev_vsync <= vsync_s;
            prev_href  <= href_s;

            // VSYNC falling edge = start of frame
            // (OV5640 default: VSYNC active high between frames)
            if (prev_vsync && !vsync_s) begin
                in_frame    <= 1'b1;
                frame_active <= 1'b1;
                cur_line    <= 9'd0;
            end

            // VSYNC rising edge = end of frame
            if (!prev_vsync && vsync_s) begin
                in_frame    <= 1'b0;
                frame_active <= 1'b0;
                frame_count <= frame_count + 8'd1;
            end

            // HREF falling edge = end of line → emit line features
            if (prev_href && !href_s && in_frame && pixel_count > 10'd0) begin
                // Compute means
                line_y_mean     <= y_sum_x3[17:10];  // y_sum*3/1024 ≈ y_sum/341 ≈ y_sum/320
                line_y_min      <= y_min_acc;
                line_y_max      <= y_max_acc;
                line_edge_count <= edge_cnt;
                line_u_mean     <= u_sum_x3[16:9];   // 160 U samples: *3/512 ≈ /170 ≈ /160
                line_v_mean     <= v_sum_x3[16:9];   // 160 V samples: *3/512 ≈ /170 ≈ /160
                line_number     <= cur_line;
                line_valid      <= 1'b1;

                // Reset accumulators for next line
                cur_line    <= cur_line + 9'd1;
                y_sum       <= 20'd0;
                y_min_acc   <= 8'hFF;
                y_max_acc   <= 8'h00;
                y_prev      <= 8'd128;
                edge_cnt    <= 8'd0;
                u_sum       <= 20'd0;
                v_sum       <= 20'd0;
                pixel_count <= 10'd0;
                byte_toggle <= 1'b0;
            end

            // Pixel capture on PCLK rising edge during HREF
            if (pclk_rise && href_s && in_frame) begin
                if (!byte_toggle) begin
                    // Even byte = Y (luminance)
                    y_sum     <= y_sum + {12'd0, pixel_sync};
                    pixel_count <= pixel_count + 10'd1;

                    // Min/max tracking
                    if (pixel_sync < y_min_acc)
                        y_min_acc <= pixel_sync;
                    if (pixel_sync > y_max_acc)
                        y_max_acc <= pixel_sync;

                    // Edge detection: |Y_current - Y_previous| > threshold
                    if (pixel_sync > y_prev + EDGE_THRESH ||
                        y_prev > pixel_sync + EDGE_THRESH)
                        edge_cnt <= edge_cnt + 8'd1;

                    y_prev <= pixel_sync;
                end else begin
                    // Odd byte = U or V (alternating)
                    // U on bytes 1, 5, 9, ... (pixel_count odd after Y)
                    // V on bytes 3, 7, 11, ...
                    if (pixel_count[0])
                        u_sum <= u_sum + {12'd0, pixel_sync};
                    else
                        v_sum <= v_sum + {12'd0, pixel_sync};
                end

                byte_toggle <= ~byte_toggle;
            end
        end
    end

endmodule
