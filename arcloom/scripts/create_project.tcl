# ============================================================
# ArcLoom Vivado Project — PYNQ-Z2 (XC7Z020-1CLG400C)
# ============================================================
#
# Usage: vivado -mode batch -source create_project.tcl
#   or:  In Vivado GUI: Tools > Run Tcl Script
#
# This creates the project, adds all sources, sets the target,
# and runs synthesis.
# ============================================================

# Project paths
set proj_name "arcloom"
set proj_dir  "[file normalize [file dirname [info script]]]/.."
set hdl_dir   "${proj_dir}/hdl"
set xdc_dir   "${proj_dir}/constraints"
set out_dir   "${proj_dir}/vivado_project"

# Create project
create_project ${proj_name} ${out_dir} -part xc7z020clg400-1 -force

# Set target language
set_property target_language Verilog [current_project]

# Add HDL sources
add_files -fileset sources_1 [glob ${hdl_dir}/*.v]
set_property top arcloom_top [current_fileset]

# Add constraints
add_files -fileset constrs_1 ${xdc_dir}/pynq_z2.xdc

# Synthesis settings — optimize for the loom's combinational depth
set_property strategy Flow_PerfOptimized_high [get_runs synth_1]
set_property STEPS.SYNTH_DESIGN.ARGS.RETIMING on [get_runs synth_1]
set_property STEPS.SYNTH_DESIGN.ARGS.KEEP_EQUIVALENT_REGISTERS on [get_runs synth_1]

# Implementation settings
set_property strategy Performance_ExploreWithRemap [get_runs impl_1]

# Run synthesis
puts "============================================"
puts " ArcLoom: Launching synthesis..."
puts " Target: XC7Z020-1CLG400C (PYNQ-Z2)"
puts "============================================"
launch_runs synth_1 -jobs 4
wait_on_run synth_1

# Check synthesis result
if {[get_property STATUS [get_runs synth_1]] != "synth_design Complete!"} {
    puts "ERROR: Synthesis failed."
    open_run synth_1
    report_timing_summary -file ${out_dir}/timing_synth.rpt
    report_utilization -file ${out_dir}/utilization_synth.rpt
    exit 1
}

# Post-synthesis reports
open_run synth_1
report_timing_summary -file ${out_dir}/timing_synth.rpt
report_utilization -file ${out_dir}/utilization_synth.rpt
report_utilization -hierarchical -file ${out_dir}/utilization_hier.rpt

puts ""
puts "============================================"
puts " Synthesis complete."
puts " Reports in: ${out_dir}/"
puts "============================================"
puts ""
puts " To continue to implementation + bitstream:"
puts "   launch_runs impl_1 -to_step write_bitstream -jobs 4"
puts "   wait_on_run impl_1"
puts ""
