# synth_esn_axi_ip.tcl -- stand-alone synthesis + implementation of the ESN AXI IP (out of context, 80 MHz)
# gives the IP's own LUT / FF / BRAM / DSP, timing and power numbers for the paper.
#   vivado -mode batch -source scripts/synth_esn_axi_ip.tcl -tclargs D:/esn_ip_platform
set root [file normalize [lindex $argv 0]]
file mkdir $root/ip_reports
create_project -in_memory -part xc7a100tcsg324-1 ooc
add_files [list $root/rtl/esn_axi_ip.v $root/rtl/esn_core.v $root/rtl/esn_readout.v $root/rtl/esn_ram.v \
    $root/rtl/esn_neuron.v $root/rtl/mac_accum_q6_10.v $root/rtl/mult_q6_10.v $root/rtl/tanh_lut.v \
    $root/rtl/reservoir_controller.v $root/rtl/address_generator.v]
add_files $root/mem/tanh.mem
set_property file_type {Memory Initialization Files} [get_files tanh.mem]
synth_design -top esn_axi_ip -part xc7a100tcsg324-1 -mode out_of_context
create_clock -period 12.500 -name aclk [get_ports aclk]
set_clock_uncertainty 0.200 [get_clocks aclk]
opt_design; place_design; route_design
report_utilization    -file $root/ip_reports/utilization.txt
report_timing_summary -file $root/ip_reports/timing.txt
report_power          -file $root/ip_reports/power.txt
puts "reports in $root/ip_reports"
