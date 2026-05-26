# ============================================================
# ArcLoom PYNQ Block Design — 3 Sensors + Camera + 12-Trit Math
# ============================================================
# Run: source C:/Users/joeta/Downloads/create_block_design.tcl
# ============================================================

set hdl_dir C:/Users/joeta/Downloads

# Create fresh project
create_project arcloom_pynq2 C:/Users/joeta/arcloom_pynq2 -part xc7z020clg400-1 -force
set_property target_language Verilog [current_project]

# Add all HDL sources
add_files -fileset sources_1 [glob ${hdl_dir}/*.v]
update_compile_order -fileset sources_1

# Create Block Design
create_bd_design "arcloom_bd"

# Add Zynq PS
create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:5.5 ps7

# Configure PS for PYNQ-Z2
apply_bd_automation -rule xilinx.com:bd_rule:processing_system7 \
    -config {make_external "FIXED_IO, DDR" Master "Disable" Slave "Disable"} \
    [get_bd_cells ps7]


# Add ArcLoom wrapper (ADDR_WIDTH=8 for 64 registers)
create_bd_cell -type module -reference arcloom_axi_wrapper arcloom_0
set_property CONFIG.C_S_AXI_ADDR_WIDTH 8 [get_bd_cells arcloom_0]

# ============================================================
# XADC — 3-channel reader (front/left/right sensors)
# ============================================================
create_bd_cell -type module -reference arcloom_xadc_reader xadc_0

# Wire XADC front sensor → AXI wrapper
connect_bd_net [get_bd_pins xadc_0/adc_data]  [get_bd_pins arcloom_0/hw_sensor_data]
connect_bd_net [get_bd_pins xadc_0/adc_valid] [get_bd_pins arcloom_0/hw_sensor_valid]

# Wire XADC left sensor → AXI wrapper
connect_bd_net [get_bd_pins xadc_0/adc_data_left]  [get_bd_pins arcloom_0/hw_sensor_data_left]
connect_bd_net [get_bd_pins xadc_0/adc_valid_left] [get_bd_pins arcloom_0/hw_sensor_valid_left]

# Wire XADC right sensor → AXI wrapper
connect_bd_net [get_bd_pins xadc_0/adc_data_right]  [get_bd_pins arcloom_0/hw_sensor_data_right]
connect_bd_net [get_bd_pins xadc_0/adc_valid_right] [get_bd_pins arcloom_0/hw_sensor_valid_right]

# Wire XADC clock and reset from PS
connect_bd_net [get_bd_pins xadc_0/clk]   [get_bd_pins ps7/FCLK_CLK0]
connect_bd_net [get_bd_pins xadc_0/rst_n] [get_bd_pins ps7/FCLK_RESET0_N]

# Route all 3 XADC analog pins to top-level ports
# A0 = VAUX1 (E17/D18) — front
create_bd_port -dir I vauxp1
create_bd_port -dir I vauxn1
connect_bd_net [get_bd_ports vauxp1] [get_bd_pins xadc_0/vauxp1]
connect_bd_net [get_bd_ports vauxn1] [get_bd_pins xadc_0/vauxn1]

# A1 = VAUX9 (E18/E19) — left
create_bd_port -dir I vauxp9
create_bd_port -dir I vauxn9
connect_bd_net [get_bd_ports vauxp9] [get_bd_pins xadc_0/vauxp9]
connect_bd_net [get_bd_ports vauxn9] [get_bd_pins xadc_0/vauxn9]

# A2 = VAUX6 (K14/J14) — right
create_bd_port -dir I vauxp6
create_bd_port -dir I vauxn6
connect_bd_net [get_bd_ports vauxp6] [get_bd_pins xadc_0/vauxp6]
connect_bd_net [get_bd_ports vauxn6] [get_bd_pins xadc_0/vauxn6]

# ============================================================
# Camera — cam_clk_0 (25MHz divider) + DVP capture
# ============================================================

# Camera clock generator — divides FCLK_CLK0 by 2 to get 25MHz
create_bd_cell -type module -reference arcloom_cam_clkgen cam_clk_0
connect_bd_net [get_bd_pins cam_clk_0/clk]   [get_bd_pins ps7/FCLK_CLK0]
connect_bd_net [get_bd_pins cam_clk_0/rst_n] [get_bd_pins ps7/FCLK_RESET0_N]

# Route clock to AR13 AND feed back into arcloom_0 to prevent trimming
create_bd_port -dir O cam_xclk
connect_bd_net [get_bd_pins cam_clk_0/xclk_out] [get_bd_ports cam_xclk]
connect_bd_net [get_bd_pins cam_clk_0/xclk_out] [get_bd_pins arcloom_0/cam_xclk_fb]

# DVP capture module
create_bd_cell -type module -reference arcloom_cam_dvp cam_dvp_0
connect_bd_net [get_bd_pins cam_dvp_0/clk]   [get_bd_pins ps7/FCLK_CLK0]
connect_bd_net [get_bd_pins cam_dvp_0/rst_n] [get_bd_pins ps7/FCLK_RESET0_N]

# DVP camera inputs from Arduino header
create_bd_port -dir I cam_pclk
create_bd_port -dir I cam_vsync
create_bd_port -dir I cam_href
create_bd_port -dir I -from 7 -to 0 cam_pixel_data
connect_bd_net [get_bd_ports cam_pclk]       [get_bd_pins cam_dvp_0/pclk]
connect_bd_net [get_bd_ports cam_vsync]      [get_bd_pins cam_dvp_0/vsync]
connect_bd_net [get_bd_ports cam_href]       [get_bd_pins cam_dvp_0/href]
connect_bd_net [get_bd_ports cam_pixel_data] [get_bd_pins cam_dvp_0/pixel_data]

# Wire DVP outputs → AXI wrapper camera inputs
connect_bd_net [get_bd_pins cam_dvp_0/line_y_mean]     [get_bd_pins arcloom_0/cam_line_y_mean]
connect_bd_net [get_bd_pins cam_dvp_0/line_y_min]      [get_bd_pins arcloom_0/cam_line_y_min]
connect_bd_net [get_bd_pins cam_dvp_0/line_y_max]      [get_bd_pins arcloom_0/cam_line_y_max]
connect_bd_net [get_bd_pins cam_dvp_0/line_edge_count] [get_bd_pins arcloom_0/cam_line_edge_count]
connect_bd_net [get_bd_pins cam_dvp_0/line_u_mean]     [get_bd_pins arcloom_0/cam_line_u_mean]
connect_bd_net [get_bd_pins cam_dvp_0/line_v_mean]     [get_bd_pins arcloom_0/cam_line_v_mean]
connect_bd_net [get_bd_pins cam_dvp_0/line_number]     [get_bd_pins arcloom_0/cam_line_number]
connect_bd_net [get_bd_pins cam_dvp_0/line_valid]      [get_bd_pins arcloom_0/cam_line_valid]
connect_bd_net [get_bd_pins cam_dvp_0/frame_active]    [get_bd_pins arcloom_0/cam_frame_active]
connect_bd_net [get_bd_pins cam_dvp_0/frame_count]     [get_bd_pins arcloom_0/cam_frame_count]

# Frame-level features — owl trick (upper/lower split) + density
connect_bd_net [get_bd_pins cam_dvp_0/frame_y_upper]     [get_bd_pins arcloom_0/cam_frame_y_upper]
connect_bd_net [get_bd_pins cam_dvp_0/frame_y_lower]     [get_bd_pins arcloom_0/cam_frame_y_lower]
connect_bd_net [get_bd_pins cam_dvp_0/frame_edge_upper]  [get_bd_pins arcloom_0/cam_frame_edge_upper]
connect_bd_net [get_bd_pins cam_dvp_0/frame_edge_lower]  [get_bd_pins arcloom_0/cam_frame_edge_lower]
connect_bd_net [get_bd_pins cam_dvp_0/frame_u_upper]     [get_bd_pins arcloom_0/cam_frame_u_upper]
connect_bd_net [get_bd_pins cam_dvp_0/frame_u_lower]     [get_bd_pins arcloom_0/cam_frame_u_lower]
connect_bd_net [get_bd_pins cam_dvp_0/frame_density]     [get_bd_pins arcloom_0/cam_frame_density]

# ============================================================
# AXI bus — arcloom_0 first (creates interconnect)
# ============================================================
apply_bd_automation -rule xilinx.com:bd_rule:axi4 \
    -config { Clk_master {Auto} Clk_slave {Auto} Clk_xbar {Auto} \
              Master {/ps7/M_AXI_GP0} Slave {/arcloom_0/S_AXI} \
              ddr_seg {Auto} intc_ip {New AXI Interconnect} master_apm {0}} \
    [get_bd_intf_pins arcloom_0/S_AXI]

# ============================================================
# Camera I2C — standalone Verilog master with IOBUF
# Auto-inits OV5640 on reset (QVGA YUV422 DVP mode)
# No AXI IIC IP needed — runs independently
# ============================================================
create_bd_cell -type module -reference arcloom_cam_i2c_iobuf cam_i2c_0
connect_bd_net [get_bd_pins cam_i2c_0/clk]   [get_bd_pins ps7/FCLK_CLK0]
connect_bd_net [get_bd_pins cam_i2c_0/rst_n] [get_bd_pins ps7/FCLK_RESET0_N]

# SDA = inout (open-drain with IOBUF inside module)
create_bd_port -dir IO cam_sda
connect_bd_net [get_bd_pins cam_i2c_0/cam_sda] [get_bd_ports cam_sda]

# SCL = output (push-pull, single master)
create_bd_port -dir O cam_scl
connect_bd_net [get_bd_pins cam_i2c_0/cam_scl] [get_bd_ports cam_scl]

# ============================================================
# Motor drive — Pmod A
# ============================================================
create_bd_port -dir O motor_ain1
create_bd_port -dir O motor_ain2
create_bd_port -dir O motor_bin1
create_bd_port -dir O motor_bin2
connect_bd_net [get_bd_pins arcloom_0/motor_ain1] [get_bd_ports motor_ain1]
connect_bd_net [get_bd_pins arcloom_0/motor_ain2] [get_bd_ports motor_ain2]
connect_bd_net [get_bd_pins arcloom_0/motor_bin1] [get_bd_ports motor_bin1]
connect_bd_net [get_bd_pins arcloom_0/motor_bin2] [get_bd_ports motor_bin2]

# ============================================================
# XDC Constraints
# ============================================================
set xdc_file [file normalize ${hdl_dir}/arcloom_pins.xdc]
set xdc_fh [open $xdc_file w]

puts $xdc_fh "## ============================================"
puts $xdc_fh "## Motor drive — Pmod A (TB6612FNG)"
puts $xdc_fh "## ============================================"
puts $xdc_fh "set_property PACKAGE_PIN Y18 \[get_ports motor_ain1\]"
puts $xdc_fh "set_property IOSTANDARD LVCMOS33 \[get_ports motor_ain1\]"
puts $xdc_fh "set_property PACKAGE_PIN Y19 \[get_ports motor_ain2\]"
puts $xdc_fh "set_property IOSTANDARD LVCMOS33 \[get_ports motor_ain2\]"
puts $xdc_fh "set_property PACKAGE_PIN Y16 \[get_ports motor_bin1\]"
puts $xdc_fh "set_property IOSTANDARD LVCMOS33 \[get_ports motor_bin1\]"
puts $xdc_fh "set_property PACKAGE_PIN Y17 \[get_ports motor_bin2\]"
puts $xdc_fh "set_property IOSTANDARD LVCMOS33 \[get_ports motor_bin2\]"

puts $xdc_fh ""
puts $xdc_fh "## ============================================"
puts $xdc_fh "## XADC Analog Inputs — 3 sensors"
puts $xdc_fh "## ============================================"
puts $xdc_fh "## A0 = VAUX1 (front) — E17/D18"
puts $xdc_fh "set_property PACKAGE_PIN E17 \[get_ports vauxp1\]"
puts $xdc_fh "set_property PACKAGE_PIN D18 \[get_ports vauxn1\]"
puts $xdc_fh "## A1 = VAUX9 (left) — E18/E19"
puts $xdc_fh "set_property PACKAGE_PIN E18 \[get_ports vauxp9\]"
puts $xdc_fh "set_property PACKAGE_PIN E19 \[get_ports vauxn9\]"
puts $xdc_fh "## A2 = VAUX6 (right) — K14/J14"
puts $xdc_fh "set_property PACKAGE_PIN K14 \[get_ports vauxp6\]"
puts $xdc_fh "set_property PACKAGE_PIN J14 \[get_ports vauxn6\]"

puts $xdc_fh ""
puts $xdc_fh "## ============================================"
puts $xdc_fh "## Camera — OV5640 DVP on Arduino Header"
puts $xdc_fh "## ============================================"
puts $xdc_fh "## From PYNQ-Z2 master XDC Arduino digital pins"
puts $xdc_fh "## AR2-AR9 = pixel data D2-D9"
puts $xdc_fh "## AR10 = VSYNC, AR11 = HREF, AR12 = PCLK"
puts $xdc_fh "## AR13 = XCLK output (25MHz)"

# Arduino digital pin package pins from master XDC
# AR0=T14, AR1=U12, AR2=U13, AR3=V13, AR4=V15, AR5=T15
# AR6=R16, AR7=U17, AR8=V17, AR9=V18, AR10=T16, AR11=R17
# AR12=P18, AR13=N17
puts $xdc_fh ""
puts $xdc_fh "## Pixel data bus D\[7:0\] → AR2-AR9"
puts $xdc_fh "set_property PACKAGE_PIN U13 \[get_ports {cam_pixel_data\[0\]}\]"
puts $xdc_fh "set_property IOSTANDARD LVCMOS33 \[get_ports {cam_pixel_data\[0\]}\]"
puts $xdc_fh "set_property PACKAGE_PIN V13 \[get_ports {cam_pixel_data\[1\]}\]"
puts $xdc_fh "set_property IOSTANDARD LVCMOS33 \[get_ports {cam_pixel_data\[1\]}\]"
puts $xdc_fh "set_property PACKAGE_PIN V15 \[get_ports {cam_pixel_data\[2\]}\]"
puts $xdc_fh "set_property IOSTANDARD LVCMOS33 \[get_ports {cam_pixel_data\[2\]}\]"
puts $xdc_fh "set_property PACKAGE_PIN T15 \[get_ports {cam_pixel_data\[3\]}\]"
puts $xdc_fh "set_property IOSTANDARD LVCMOS33 \[get_ports {cam_pixel_data\[3\]}\]"
puts $xdc_fh "set_property PACKAGE_PIN R16 \[get_ports {cam_pixel_data\[4\]}\]"
puts $xdc_fh "set_property IOSTANDARD LVCMOS33 \[get_ports {cam_pixel_data\[4\]}\]"
puts $xdc_fh "set_property PACKAGE_PIN U17 \[get_ports {cam_pixel_data\[5\]}\]"
puts $xdc_fh "set_property IOSTANDARD LVCMOS33 \[get_ports {cam_pixel_data\[5\]}\]"
puts $xdc_fh "set_property PACKAGE_PIN V17 \[get_ports {cam_pixel_data\[6\]}\]"
puts $xdc_fh "set_property IOSTANDARD LVCMOS33 \[get_ports {cam_pixel_data\[6\]}\]"
puts $xdc_fh "set_property PACKAGE_PIN V18 \[get_ports {cam_pixel_data\[7\]}\]"
puts $xdc_fh "set_property IOSTANDARD LVCMOS33 \[get_ports {cam_pixel_data\[7\]}\]"

puts $xdc_fh ""
puts $xdc_fh "## VSYNC = AR10, HREF = AR11, PCLK = AR12"
puts $xdc_fh "set_property PACKAGE_PIN T16 \[get_ports cam_vsync\]"
puts $xdc_fh "set_property IOSTANDARD LVCMOS33 \[get_ports cam_vsync\]"
puts $xdc_fh "set_property PACKAGE_PIN R17 \[get_ports cam_href\]"
puts $xdc_fh "set_property IOSTANDARD LVCMOS33 \[get_ports cam_href\]"
puts $xdc_fh "set_property PACKAGE_PIN P18 \[get_ports cam_pclk\]"
puts $xdc_fh "set_property IOSTANDARD LVCMOS33 \[get_ports cam_pclk\]"

puts $xdc_fh ""
puts $xdc_fh "## XCLK output = AR13 (25MHz clock to camera)"
puts $xdc_fh "set_property PACKAGE_PIN N17 \[get_ports cam_xclk\]"
puts $xdc_fh "set_property IOSTANDARD LVCMOS33 \[get_ports cam_xclk\]"

puts $xdc_fh ""
puts $xdc_fh "## I2C — Arduino header SDA/SCL (Verilog I2C master)"
puts $xdc_fh "set_property PACKAGE_PIN P16 \[get_ports cam_sda\]"
puts $xdc_fh "set_property IOSTANDARD LVCMOS33 \[get_ports cam_sda\]"
puts $xdc_fh "set_property PULLUP true \[get_ports cam_sda\]"
puts $xdc_fh "set_property PACKAGE_PIN P15 \[get_ports cam_scl\]"
puts $xdc_fh "set_property IOSTANDARD LVCMOS33 \[get_ports cam_scl\]"
puts $xdc_fh "set_property PULLUP true \[get_ports cam_scl\]"

close $xdc_fh
add_files -fileset constrs_1 $xdc_file

# Validate
validate_bd_design
save_bd_design

# Generate targets and wrapper
generate_target all [get_files arcloom_bd.bd]
make_wrapper -files [get_files arcloom_bd.bd] -top
add_files -norecurse [glob C:/Users/joeta/arcloom_pynq2/arcloom_pynq2.gen/sources_1/bd/arcloom_bd/hdl/arcloom_bd_wrapper.v]
set_property top arcloom_bd_wrapper [current_fileset]
update_compile_order -fileset sources_1

# Raise pwropt fanin/fanout limit — wider SPPU (64 inputs × 9 fields)
# exceeds the default ratio. This prevents the HACOOException in opt_design.
set_param pwropt.maxFaninFanoutToNetRatio 10000

# Synthesize
launch_runs synth_1 -jobs 10
wait_on_run synth_1

puts ""
puts "============================================"
puts " Synthesis complete."
puts " 3 sensors + camera clock + DVP + 12-trit MathLoom"
puts "============================================"
