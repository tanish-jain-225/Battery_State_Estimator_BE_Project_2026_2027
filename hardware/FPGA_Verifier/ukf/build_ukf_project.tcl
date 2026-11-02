# Rebuild the UKF Vivado project (separate from the ESN project).
set root [file normalize [file dirname [info script]]]
create_project UKF_FPGA $root/vivado_ukf -part xc7a100tcsg324-1 -force
add_files -fileset sources_1 $root/rtl/ukf_core.v
foreach m {ukf_ocv.mem ukf_slope.mem} {
    add_files -fileset sources_1 $root/sim/$m
    set_property used_in_synthesis true  [get_files $m]
    set_property used_in_simulation true [get_files $m]
}
add_files -fileset constrs_1 $root/rtl/ukf_core.xdc
set_property top ukf_core [get_filesets sources_1]
add_files -fileset sim_1 [list $root/rtl/tb_ukf_core.v $root/sim/ukf_stim.mem]
set_property top tb_ukf_core [get_filesets sim_1]
update_compile_order -fileset sources_1
update_compile_order -fileset sim_1
puts "UKF project ready: $root/vivado_ukf/UKF_FPGA.xpr"
