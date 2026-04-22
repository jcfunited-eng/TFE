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

# Add XADC reader — direct PL hardware sensor path
create_bd_cell -type module -reference arcloom_xadc_reader xadc_0

# Wire XADC reader outputs → AXI wrapper hw_sensor inputs
connect_bd_net [get_bd_pins xadc_0/adc_data]  [get_bd_pins arcloom_0/hw_sensor_data]
connect_bd_net [get_bd_pins xadc_0/adc_valid] [get_bd_pins arcloom_0/hw_sensor_valid]

# Wire XADC clock and reset from PS
connect_bd_net [get_bd_pins xadc_0/clk]   [get_bd_pins ps7/FCLK_CLK0]
connect_bd_net [get_bd_pins xadc_0/rst_n] [get_bd_pins ps7/FCLK_RESET0_N]

# Make XADC analog inputs external (physical pins)
create_bd_port -dir I vauxp3
create_bd_port -dir I vauxn3
connect_bd_net [get_bd_ports vauxp3] [get_bd_pins xadc_0/vauxp3]
connect_bd_net [get_bd_ports vauxn3] [get_bd_pins xadc_0/vauxn3]

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
