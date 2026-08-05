// ============================================================
// ArcLoom Camera Clock Generator — 24MHz XCLK for OV5640
// ============================================================
//
// Generates a 24MHz clock from the 100MHz system clock.
// 100MHz / 4 = 25MHz (close enough — OV5640 accepts 6-27MHz)
// Using divide-by-4 for clean 50% duty cycle.
//
// Output: 25MHz clock on AR13 → camera XC pin
//
// Target: PYNQ-Z2 (XC7Z020-1CLG400C)
// ============================================================

(* DONT_TOUCH = "TRUE" *)
module arcloom_cam_clkgen (
    input  wire clk,      // 100MHz system clock
    input  wire rst_n,
    output reg  xclk_out  // ~25MHz camera clock
);

    reg [1:0] cnt;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cnt      <= 2'd0;
            xclk_out <= 1'b0;
        end else begin
            cnt <= cnt + 2'd1;
            if (cnt == 2'd1)
                xclk_out <= 1'b1;
            else if (cnt == 2'd3)
                xclk_out <= 1'b0;
        end
    end

endmodule
