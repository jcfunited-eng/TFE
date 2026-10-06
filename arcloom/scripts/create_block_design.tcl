# ============================================================
# ArcLoom PYNQ Block Design — 3 Sensors + 12-Trit Math (Camera-Free)
# ============================================================
# Run in Vivado Tcl Console:
#   source C:/Users/joeta/Downloads/arcloom_hdl/create_block_design.tcl
# ============================================================

# Close any currently open project before creating fresh project
catch {close_project}

if {[file exists "C:/Users/joeta/Downloads/arcloom_hdl/arcloom_axi_wrapper.v"]} {
    set hdl_dir "C:/Users/joeta/Downloads/arcloom_hdl"
    puts "=== Using HDL directory: C:/Users/joeta/Downloads/arcloom_hdl ==="
} else {
    set hdl_dir "C:/Users/joeta/Downloads"
    puts "=== Using HDL directory: C:/Users/joeta/Downloads ==="
}

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

# Wire XADC front sensor -> AXI wrapper
connect_bd_net [get_bd_pins xadc_0/adc_data]  [get_bd_pins arcloom_0/hw_sensor_data]
connect_bd_net [get_bd_pins xadc_0/adc_valid] [get_bd_pins arcloom_0/hw_sensor_valid]

# Wire XADC left sensor -> AXI wrapper
connect_bd_net [get_bd_pins xadc_0/adc_data_left]  [get_bd_pins arcloom_0/hw_sensor_data_left]
connect_bd_net [get_bd_pins xadc_0/adc_valid_left] [get_bd_pins arcloom_0/hw_sensor_valid_left]

# Wire XADC right sensor -> AXI wrapper
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
# AXI bus — arcloom_0 first (creates interconnect)
# ============================================================
apply_bd_automation -rule xilinx.com:bd_rule:axi4 \
    -config { Clk_master {Auto} Clk_slave {Auto} Clk_xbar {Auto} \
              Master {/ps7/M_AXI_GP0} Slave {/arcloom_0/S_AXI} \
              ddr_seg {Auto} intc_ip {New AXI Interconnect} master_apm {0}} \
    [get_bd_intf_pins arcloom_0/S_AXI]

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

# Raise pwropt fanin/fanout limit
set_param pwropt.maxFaninFanoutToNetRatio 10000

# Synthesize
launch_runs synth_1 -jobs 10
wait_on_run synth_1

puts ""
puts "============================================"
puts " Synthesis complete. Starting implementation..."
puts "============================================"

# Disable power optimization steps that hang on wide memory
set_property STEPS.POWER_OPT_DESIGN.IS_ENABLED false [get_runs impl_1]
set_property STEPS.POST_ROUTE_PHYS_OPT_DESIGN.IS_ENABLED false [get_runs impl_1]
set_property STEPS.OPT_DESIGN.ARGS.DIRECTIVE {NoBramPowerOpt} [get_runs impl_1]

# Run implementation
launch_runs impl_1 -jobs 10
wait_on_run impl_1

# Generate bitstream
launch_runs impl_1 -to_step write_bitstream -jobs 10
wait_on_run impl_1

puts ""
puts "============================================"
puts " Bitstream complete."
puts " .bit and .hwh in:"
puts " C:/Users/joeta/arcloom_pynq2/arcloom_pynq2.runs/impl_1/"
puts "============================================"
