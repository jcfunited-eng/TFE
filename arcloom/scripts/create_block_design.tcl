# ============================================================
# ArcLoom PYNQ Block Design — Clean Build
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

# Add ArcLoom wrapper
create_bd_cell -type module -reference arcloom_axi_wrapper arcloom_0

# Force ADDR_WIDTH to 4
set_property CONFIG.C_S_AXI_ADDR_WIDTH 4 [get_bd_cells arcloom_0]

# XADC hardware sensor path — DISABLED for now.
# Tying VAUXP/VAUXN to 0 reads 0V, not the actual sensor.
# The analog pins need proper routing which requires more work.
# For now, use the software sensor path (ARM reads sensor, writes via AXI).
#
# Tie hw_sensor_valid to GND so software path is selected by the mux.
create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 gnd_const
set_property CONFIG.CONST_VAL 0 [get_bd_cells gnd_const]
connect_bd_net [get_bd_pins gnd_const/dout] [get_bd_pins arcloom_0/hw_sensor_valid]

# Tie hw_sensor_data to 0 (unused when valid=0)
create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 gnd_data
set_property CONFIG.CONST_WIDTH 16 [get_bd_cells gnd_data]
set_property CONFIG.CONST_VAL 0 [get_bd_cells gnd_data]
connect_bd_net [get_bd_pins gnd_data/dout] [get_bd_pins arcloom_0/hw_sensor_data]

# Wire AXI
apply_bd_automation -rule xilinx.com:bd_rule:axi4 \
    -config { Clk_master {Auto} Clk_slave {Auto} Clk_xbar {Auto} \
              Master {/ps7/M_AXI_GP0} Slave {/arcloom_0/S_AXI} \
              ddr_seg {Auto} intc_ip {New AXI Interconnect} master_apm {0}} \
    [get_bd_intf_pins arcloom_0/S_AXI]

# Validate
validate_bd_design
save_bd_design

# Generate targets and wrapper
generate_target all [get_files arcloom_bd.bd]
make_wrapper -files [get_files arcloom_bd.bd] -top
add_files -norecurse [glob C:/Users/joeta/arcloom_pynq2/arcloom_pynq2.gen/sources_1/bd/arcloom_bd/hdl/arcloom_bd_wrapper.v]
set_property top arcloom_bd_wrapper [current_fileset]
update_compile_order -fileset sources_1

# Synthesize
launch_runs synth_1 -jobs 10
wait_on_run synth_1

puts ""
puts "============================================"
puts " Synthesis complete. Check MathLoom nets:"
puts "   open_run synth_1"
puts "   get_nets *ml_product*"
puts "============================================"
