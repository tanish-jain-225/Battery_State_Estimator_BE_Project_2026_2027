# build_platform.tcl -- Vivado 2023.1 project + bitstream for the ESN/EKF/UKF platform on the Arty A7-100T
#   vivado -mode batch -source scripts/build_platform.tcl          (or Tools > Run Tcl Script)
# Produces vivado/esn_platform.runs/impl_1/esn_platform_top.bit and reports in vivado/reports/.
# NOTE: this project uses NO Block-Memory-Generator IP (memories are inferred by rtl/esn_ram.v), so the old
#       tiny_bram_models.v / *_bram IP files must NOT be added to it.
set root [file normalize [file dirname [info script]]/..]
create_project esn_platform $root/vivado -part xc7a100tcsg324-1 -force
add_files -fileset sources_1 [glob $root/rtl/*.v]
add_files -fileset sources_1 $root/mem/tanh.mem
set_property file_type {Memory Initialization Files} [get_files tanh.mem]
add_files -fileset constrs_1 $root/xdc/esn_platform_top.xdc
set_property top esn_platform_top [get_filesets sources_1]
add_files -fileset sim_1 $root/tb/tb_esn_platform.v
set_property top tb_esn_platform [get_filesets sim_1]
update_compile_order -fileset sources_1
if {[llength $argv] && [lindex $argv 0] eq "noimpl"} { puts "project ready"; return }
launch_runs synth_1 -jobs 4; wait_on_run synth_1
launch_runs impl_1 -to_step write_bitstream -jobs 4; wait_on_run impl_1
open_run impl_1
file mkdir $root/vivado/reports
report_utilization    -file $root/vivado/reports/utilization.txt
report_timing_summary -file $root/vivado/reports/timing.txt
report_power          -file $root/vivado/reports/power.txt
puts "bitstream: $root/vivado/esn_platform.runs/impl_1/esn_platform_top.bit"
