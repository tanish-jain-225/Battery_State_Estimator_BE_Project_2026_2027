# Builds the JTAG-AXI + ESN IP test system for the Arty A7-100T
open_project D:/sys_chk/sys_chk.xpr
set xdc D:/sys_chk/sys_pins.xdc
set f [open $xdc w]
puts $f {set_property -dict { PACKAGE_PIN E3 IOSTANDARD LVCMOS33 } [get_ports clk100]}
puts $f {create_clock -period 10.000 -name clk100 [get_ports clk100]}
puts $f {set_property -dict { PACKAGE_PIN C2 IOSTANDARD LVCMOS33 } [get_ports rstn]}
puts $f {set_false_path -from [get_ports rstn]}
puts $f {set_property CFGBVS VCCO [current_design]}
puts $f {set_property CONFIG_VOLTAGE 3.3 [current_design]}
close $f
add_files -fileset constrs_1 -norecurse $xdc
set_property top sys_wrapper [current_fileset]
update_compile_order -fileset sources_1
launch_runs impl_1 -to_step write_bitstream -jobs 2
wait_on_run impl_1
puts "RUN STATUS: [get_property STATUS [get_runs impl_1]]"
open_run impl_1
report_timing_summary -file D:/sys_chk/sys_timing.txt
report_utilization -file D:/sys_chk/sys_util.txt
puts "BITSTREAM: [glob -nocomplain D:/sys_chk/sys_chk.runs/impl_1/*.bit]"
close_project
