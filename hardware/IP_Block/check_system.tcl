# Validates esn_axi_ip inside a real AXI system: JTAG-to-AXI master -> interconnect -> ESN IP,
# with ESN stream out looped to stream in through an AXIS FIFO (both 64-bit).
catch {close_project}
create_project -force sys_chk D:/sys_chk -part xc7a100tcsg324-1
set_property ip_repo_paths D:/esn_ip_platform/ip_repo [current_project]
update_ip_catalog -rebuild
create_bd_design sys

create_bd_port -dir I -type clk -freq_hz 100000000 clk100
create_bd_port -dir I -type rst rstn
set_property CONFIG.POLARITY ACTIVE_LOW [get_bd_ports rstn]

set cw [create_bd_cell -type ip -vlnv [lindex [get_ipdefs xilinx.com:ip:clk_wiz:*] 0] clkw]
set_property -dict [list CONFIG.PRIM_IN_FREQ {100.000} CONFIG.CLKOUT1_REQUESTED_OUT_FREQ {80.000} CONFIG.USE_RESET {false}] $cw
set rs [create_bd_cell -type ip -vlnv [lindex [get_ipdefs xilinx.com:ip:proc_sys_reset:*] 0] rst]
set jt [create_bd_cell -type ip -vlnv [lindex [get_ipdefs xilinx.com:ip:jtag_axi:*] 0] jtag]
set ic [create_bd_cell -type ip -vlnv [lindex [get_ipdefs xilinx.com:ip:smartconnect:*] 0] ic]
set_property -dict [list CONFIG.NUM_SI {1} CONFIG.NUM_MI {1}] $ic
set esn [create_bd_cell -type ip -vlnv [lindex [get_ipdefs *esn_axi_ip*] 0] esn]
set ff [create_bd_cell -type ip -vlnv [lindex [get_ipdefs xilinx.com:ip:axis_data_fifo:*] 0] lpf]
set_property CONFIG.TDATA_NUM_BYTES {8} $ff

connect_bd_net [get_bd_ports clk100] [get_bd_pins clkw/clk_in1]
connect_bd_net [get_bd_ports rstn] [get_bd_pins rst/ext_reset_in]
connect_bd_net [get_bd_pins clkw/locked] [get_bd_pins rst/dcm_locked]
set clk [get_bd_pins clkw/clk_out1]
foreach p {rst/slowest_sync_clk jtag/aclk ic/aclk esn/aclk lpf/s_axis_aclk} { connect_bd_net $clk [get_bd_pins $p] }
foreach p {jtag/aresetn ic/aresetn esn/aresetn lpf/s_axis_aresetn} { connect_bd_net [get_bd_pins rst/peripheral_aresetn] [get_bd_pins $p] }
connect_bd_intf_net [get_bd_intf_pins jtag/M_AXI] [get_bd_intf_pins ic/S00_AXI]
connect_bd_intf_net [get_bd_intf_pins ic/M00_AXI] [get_bd_intf_pins esn/s_axi]
connect_bd_intf_net [get_bd_intf_pins esn/m_axis] [get_bd_intf_pins lpf/S_AXIS]
connect_bd_intf_net [get_bd_intf_pins lpf/M_AXIS] [get_bd_intf_pins esn/s_axis]

assign_bd_address
puts "ESN INTERFACES:"; foreach i [get_bd_intf_pins esn/*] { puts "  $i" }
validate_bd_design
save_bd_design
puts "=== VALIDATE OK ==="
make_wrapper -files [get_files sys.bd] -top
add_files -norecurse [glob D:/sys_chk/sys_chk.gen/sources_1/bd/sys/hdl/sys_wrapper.v]
update_compile_order -fileset sources_1
close_project