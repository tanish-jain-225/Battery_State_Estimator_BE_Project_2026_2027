# Session 2: synthesis + implementation + bitstream
open_project D:/sys_stream/sys_stream.xpr
set_property top sys_wrapper [current_fileset]
launch_runs impl_1 -to_step write_bitstream -jobs 1
wait_on_run impl_1
puts "RUN STATUS: [get_property STATUS [get_runs impl_1]]"
open_run impl_1
report_timing_summary -file D:/sys_stream/timing.txt
report_utilization -file D:/sys_stream/util.txt
puts "BITSTREAM: [glob -nocomplain D:/sys_stream/sys_stream.runs/impl_1/*.bit]"
close_project
