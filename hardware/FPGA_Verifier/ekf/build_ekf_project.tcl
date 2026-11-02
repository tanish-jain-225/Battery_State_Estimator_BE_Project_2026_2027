# Rebuild the EKF Vivado project (separate from the ESN project).
set root [file normalize [file dirname [info script]]]
create_project EKF_FPGA $root/vivado_ekf -part xc7a100tcsg324-1 -force
add_files -fileset sources_1 $root/rtl/ekf_core.v
foreach m {ocv_lut.mem slope_lut.mem} {
    add_files -fileset sources_1 $root/sim/$m
    set_property used_in_synthesis true  [get_files $m]
    set_property used_in_simulation true [get_files $m]
}
add_files -fileset constrs_1 $root/rtl/ekf_core.xdc
set_property top ekf_core [get_filesets sources_1]
add_files -fileset sim_1 [list $root/rtl/tb_ekf_core.v $root/sim/stim.mem]
set_property top tb_ekf_core [get_filesets sim_1]
update_compile_order -fileset sources_1
update_compile_order -fileset sim_1
puts "EKF project ready: $root/vivado_ekf/EKF_FPGA.xpr"
