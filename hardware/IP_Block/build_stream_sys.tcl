# Stream-mode test system (no DMA / no burst interconnect):
#   JTAG-AXI -> SmartConnect (AXI4-Lite only) -> {ESN regs, AXI4-Stream FIFO regs}
#   FIFO TX (32b) -> 32->64 converter -> ESN s_axis ... ESN m_axis (64b) -> 64->32 converter -> FIFO RX
catch {close_project}
create_project -force sys_stream D:/sys_stream -part xc7a100tcsg324-1
set_property ip_repo_paths D:/esn_ip_platform/ip_repo [current_project]
update_ip_catalog -rebuild
create_bd_design sys
create_bd_port -dir I -type clk -freq_hz 100000000 clk100
create_bd_port -dir I -type rst rstn
set_property CONFIG.POLARITY ACTIVE_LOW [get_bd_ports rstn]

proc mk {vlnv name} { return [create_bd_cell -type ip -vlnv [lindex [get_ipdefs $vlnv] 0] $name] }
set cw  [mk xilinx.com:ip:clk_wiz:*          clkw]
set_property -dict [list CONFIG.PRIM_IN_FREQ {100.000} CONFIG.CLKOUT1_REQUESTED_OUT_FREQ {80.000} CONFIG.USE_RESET {false}] $cw
set rs  [mk xilinx.com:ip:proc_sys_reset:*   rst]
set jt  [mk xilinx.com:ip:jtag_axi:*         jtag]
set ic  [mk xilinx.com:ip:smartconnect:*     ic]
set_property -dict [list CONFIG.NUM_SI {1} CONFIG.NUM_MI {2}] $ic
set esn [mk *esn_axi_ip*                     esn]
set ff  [mk xilinx.com:ip:axi_fifo_mm_s:*    fifo]
catch {set_property CONFIG.C_USE_TX_CTRL {0} $ff}
set up  [mk xilinx.com:ip:axis_dwidth_converter:* up]
set_property -dict [list CONFIG.S_TDATA_NUM_BYTES {4} CONFIG.M_TDATA_NUM_BYTES {8}] $up
set dn  [mk xilinx.com:ip:axis_dwidth_converter:* dn]
set_property -dict [list CONFIG.S_TDATA_NUM_BYTES {8} CONFIG.M_TDATA_NUM_BYTES {4}] $dn

connect_bd_net [get_bd_ports clk100] [get_bd_pins clkw/clk_in1]
connect_bd_net [get_bd_ports rstn] [get_bd_pins rst/ext_reset_in]
connect_bd_net [get_bd_pins clkw/locked] [get_bd_pins rst/dcm_locked]
set clk [get_bd_pins clkw/clk_out1]
foreach p {rst/slowest_sync_clk jtag/aclk ic/aclk esn/aclk fifo/s_axi_aclk up/aclk dn/aclk} { connect_bd_net $clk [get_bd_pins $p] }
foreach p {jtag/aresetn ic/aresetn esn/aresetn fifo/s_axi_aresetn up/aresetn dn/aresetn} { connect_bd_net [get_bd_pins rst/peripheral_aresetn] [get_bd_pins $p] }
connect_bd_intf_net [get_bd_intf_pins jtag/M_AXI]       [get_bd_intf_pins ic/S00_AXI]
connect_bd_intf_net [get_bd_intf_pins ic/M00_AXI]       [get_bd_intf_pins esn/s_axi]
connect_bd_intf_net [get_bd_intf_pins ic/M01_AXI]       [get_bd_intf_pins fifo/S_AXI]
connect_bd_intf_net [get_bd_intf_pins fifo/AXI_STR_TXD] [get_bd_intf_pins up/S_AXIS]
connect_bd_intf_net [get_bd_intf_pins up/M_AXIS]        [get_bd_intf_pins esn/s_axis]
connect_bd_intf_net [get_bd_intf_pins esn/m_axis]       [get_bd_intf_pins dn/S_AXIS]
connect_bd_intf_net [get_bd_intf_pins dn/M_AXIS]        [get_bd_intf_pins fifo/AXI_STR_RXD]

set jd [get_bd_addr_spaces jtag/Data]
assign_bd_address -offset 0x00000000 -range 4K  -target_address_space $jd [get_bd_addr_segs esn/s_axi/reg0]
assign_bd_address -offset 0x00010000 -range 64K -target_address_space $jd [lindex [get_bd_addr_segs -of_objects [get_bd_cells fifo]] 0]
validate_bd_design
save_bd_design
puts "=== VALIDATE OK ==="
foreach s [get_bd_addr_segs -of_objects $jd] { puts "ADDR $s [get_property OFFSET $s]" }

make_wrapper -files [get_files sys.bd] -top
add_files -norecurse [glob D:/sys_stream/sys_stream.gen/sources_1/bd/sys/hdl/sys_wrapper.v]
set xdc D:/sys_stream/pins.xdc
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
report_timing_summary -file D:/sys_stream/timing.txt
report_utilization -file D:/sys_stream/util.txt
puts "BITSTREAM: [glob -nocomplain D:/sys_stream/sys_stream.runs/impl_1/*.bit]"
close_project