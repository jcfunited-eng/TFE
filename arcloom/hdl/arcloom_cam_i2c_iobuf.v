// ============================================================
// ArcLoom Camera I2C — IOBUF wrapper for block design
// ============================================================
//
// Wraps arcloom_cam_i2c with proper IOBUF for SDA (open-drain)
// and push-pull SCL (single master, no clock stretching).
//
// Standalone module — does NOT connect to arcloom_axi_wrapper.
// Runs OV5640 init automatically on reset, then goes idle.
//
// Target: PYNQ-Z2 Arduino header SDA=P16, SCL=P15
// ============================================================

module arcloom_cam_i2c_iobuf (
    input  wire clk,
    input  wire rst_n,
    inout  wire cam_sda,
    output wire cam_scl,
    output wire init_done,
    output wire [6:0] init_step,

    // Runtime I2C write/read (from AXI wrapper)
    input  wire [15:0] rt_reg_addr,
    input  wire [7:0]  rt_reg_data,
    input  wire        rt_write,
    input  wire        rt_read,
    output wire        rt_busy,
    output wire        rt_done,
    output wire [7:0]  rt_read_data,
    output wire        rt_read_valid,

    // I2C bus monitor (read port)
    input  wire [9:0]  mon_rd_addr,
    output wire [31:0] mon_rd_data,
    output wire [9:0]  mon_write_count,
    output wire        mon_overflow
);

    wire sda_out, sda_oe, sda_in;
    wire scl_out, scl_oe;

    // SDA: open-drain via IOBUF
    // Drive low when oe=1 and out=0; tri-state otherwise (pull-up provides high)
    IOBUF #(.DRIVE(12), .SLEW("SLOW")) sda_iobuf (
        .O(sda_in),
        .IO(cam_sda),
        .I(1'b0),
        .T(~sda_oe | sda_out)
    );

    // SCL: push-pull (single master, no clock stretching from OV5640)
    assign cam_scl = (scl_oe) ? scl_out : 1'b1;

    arcloom_cam_i2c i2c_inst (
        .clk(clk),
        .rst_n(rst_n),
        .sda_out(sda_out),
        .sda_oe(sda_oe),
        .sda_in(sda_in),
        .scl_out(scl_out),
        .scl_oe(scl_oe),
        .init_done(init_done),
        .init_step(init_step),
        .rt_reg_addr(rt_reg_addr),
        .rt_reg_data(rt_reg_data),
        .rt_write(rt_write),
        .rt_read(rt_read),
        .rt_busy(rt_busy),
        .rt_done(rt_done),
        .rt_read_data(rt_read_data),
        .rt_read_valid(rt_read_valid)
    );

    // ---- I2C Bus Monitor (passive, taps internal wires) ----
    arcloom_i2c_monitor i2c_mon (
        .clk(clk), .rst_n(rst_n),
        .scl_in(cam_scl),    // tap SCL from actual pin output
        .sda_in(sda_in),     // tap SDA from IOBUF (actual bus state)
        .read_addr(mon_rd_addr),
        .read_data(mon_rd_data),
        .write_count(mon_write_count),
        .overflow(mon_overflow)
    );

endmodule
