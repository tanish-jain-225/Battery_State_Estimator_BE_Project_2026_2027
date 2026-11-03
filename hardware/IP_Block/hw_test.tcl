# Programs the board and reads/writes the ESN IP registers over JTAG-to-AXI
open_hw_manager
connect_hw_server
open_hw_target
set dev [lindex [get_hw_devices xc7a100t*] 0]
current_hw_device $dev
set_property PROGRAM.FILE D:/sys_chk/sys_chk.runs/impl_1/sys_wrapper.bit $dev
program_hw_devices $dev
refresh_hw_device $dev
set ax [lindex [get_hw_axis] 0]
proc rd {ax a} {
  create_hw_axi_txn -force rt $ax -type read -address [format %08X $a] -len 1
  run_hw_axi rt
  return [string toupper [lindex [report_hw_axi_txn rt] end]]
}
proc wr {ax a d} {
  create_hw_axi_txn -force wt $ax -type write -address [format %08X $a] -data [format %08X $d] -len 1
  run_hw_axi wt
}
set id   [rd $ax 0x00]
set caps [rd $ax 0x04]
puts "ID   = $id   (expect 45534E31)"
puts "CAPS = $caps (expect 04006404)"
wr $ax 0x08 2          ;# CTRL.CLEAR
set st [rd $ax 0x0C]
set ts [rd $ax 0x18]
puts "STATUS = $st (expect 00000000)"
puts "TIMESTEP = $ts (expect 00000000)"
if {[string match *45534E31 $id] && [string match *04006404 $caps]} { puts "=== IP REACHABLE OVER AXI: PASS ===" } else { puts "=== FAIL ===" }
