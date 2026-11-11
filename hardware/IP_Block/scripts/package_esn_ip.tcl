# package_esn_ip.tcl -- package esn_axi_ip as a Vivado IP-XACT IP (Vivado 2023.1)
#
#   vivado -mode batch -source scripts/package_esn_ip.tcl -tclargs <path-to-esn_ip-folder>
#
# Result: <esn_ip>/ip_repo/vesit_esn_axi_ip_1.0/  (add <esn_ip>/ip_repo to IP Repository Paths,
#         then "ESN Accelerator" appears in the IP Catalog and in Block Designs)
set root [file normalize [lindex $argv 0]]
set vendor  "vesit.ac.in"
set library "user"
set name    "esn_axi_ip"
set version "1.0"
set ipdir   "$root/ip_repo/${vendor}_${library}_${name}_${version}"

create_project -in_memory -part xc7a100tcsg324-1 pkg_esn
set_property target_language Verilog [current_project]

add_files [list \
    $root/rtl/esn_axi_ip.v   $root/rtl/esn_core.v   $root/rtl/esn_core_fast.v $root/rtl/esn_readout.v  $root/rtl/esn_ram.v \
    $root/rtl/esn_neuron.v   $root/rtl/mac_accum_q6_10.v  $root/rtl/mult_q6_10.v \
    $root/rtl/tanh_lut.v     $root/rtl/reservoir_controller.v  $root/rtl/address_generator.v ]
add_files $root/mem/tanh.mem
set_property file_type {Memory Initialization Files} [get_files tanh.mem]
set_property top $name [current_fileset]
update_compile_order -fileset sources_1

ipx::package_project -root_dir $ipdir -vendor $vendor -library $library -taxonomy /UserIP \
                     -import_files -set_current true
set core [ipx::current_core]
set_property name         $name                         $core
set_property version      $version                      $core
set_property display_name "ESN Accelerator (battery SOC/SOH)" $core
set_property description  "Echo State Network reservoir + linear SOC/SOH readout, Q6.10 fixed point, AXI4-Lite control, AXI4-Stream data" $core
set_property vendor_display_name "VESIT"                $core
set_property supported_families {artix7 Production kintex7 Production virtex7 Production zynq Production} $core

# ---- bus interfaces ----
ipx::infer_bus_interfaces $core
# clock / reset association
set clk [ipx::get_bus_interfaces aclk -of_objects $core]
if {$clk eq ""} { ipx::infer_bus_interface aclk xilinx.com:signal:clock_rtl:1.0 $core ; set clk [ipx::get_bus_interfaces aclk -of_objects $core] }
ipx::add_bus_parameter ASSOCIATED_BUSIF $clk
set_property value "s_axi:s_axis:m_axis" [ipx::get_bus_parameters ASSOCIATED_BUSIF -of_objects $clk]
ipx::add_bus_parameter ASSOCIATED_RESET $clk
set_property value "aresetn" [ipx::get_bus_parameters ASSOCIATED_RESET -of_objects $clk]

# AXI4-Lite address space: 256 bytes
set mm [ipx::add_memory_map s_axi $core]
set_property slave_memory_map_ref s_axi [ipx::get_bus_interfaces s_axi -of_objects $core]
set ab [ipx::add_address_block reg0 $mm]
set_property range 256 $ab

# ---- GUI parameters ----
foreach {p lbl dflt mn mx} {N_IN "Number of inputs" 4 2 64  N_RES "Reservoir neurons" 100 2 1024  T_MAX "Window length (power of 2)" 64 2 1024} {
    set pr [ipx::get_user_parameters $p -of_objects $core]
    set_property display_name $lbl $pr
    set_property value $dflt $pr
    set_property value_validation_type range_long $pr
    set_property value_validation_range_minimum $mn $pr
    set_property value_validation_range_maximum $mx $pr
}
set_property enablement_value false [ipx::get_user_parameters READ_LAT -of_objects $core]

ipx::create_xgui_files $core
ipx::update_checksums $core
ipx::check_integrity $core
ipx::save_core $core
close_project
puts "ESN IP packaged in $ipdir"
