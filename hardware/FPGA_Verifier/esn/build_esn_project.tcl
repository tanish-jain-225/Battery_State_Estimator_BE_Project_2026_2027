# Rebuild the ESN Vivado project from this folder.
# Vivado 2023.1:  Tools -> Run Tcl Script -> build_esn_project.tcl
#   (or: vivado -mode batch -source build_esn_project.tcl)
set root [file normalize [file dirname [info script]]]
set part xc7a100tcsg324-1
create_project ESN_FPGA $root/vivado_esn -part $part -force

# ---- RTL, memory file, constraints ----
add_files -fileset sources_1 [glob $root/rtl/*.v]
add_files -fileset sources_1 $root/mem/tanh.mem
set_property used_in_synthesis true  [get_files tanh.mem]
set_property used_in_simulation true [get_files tanh.mem]
add_files -fileset constrs_1 $root/xdc/esn_top.xdc
set_property top esn_top [get_filesets sources_1]

# ---- Block-memory IP cores (Block Memory Generator 8.4), 16-bit ----
# Reverse-engineered from the original project's synthesis log and post-route reports:
#   win_bram, w_bram, bias_bram : 6 ports (clka ena wea addra dina douta) -> Single Port RAM, ENA pin
#   input_bram                  : 5 ports (clka wea addra dina douta)     -> Single Port RAM, always enabled
#   state_bram                  : clka ena wea addra dina / clkb enb addrb doutb -> Simple Dual Port RAM
#   depths from the .coe files; primitives: w_bram = 5 x RAMB36, the others 1 x RAMB18 each.
# BRAM_MODE ORIGINAL = exactly as above (wea/dina left unconnected, as before -> 68 critical warnings)
# BRAM_MODE ROM      = same memories as read-only ROMs (identical read behaviour, no warnings)
# READ_REG 0 = read latency 1 (what the RTL FSM assumes). If the bit-exact check fails, set 1 and rebuild.
set BRAM_MODE ROM
set READ_REG  0
proc make_mem {name depth coe ena} {
    global BRAM_MODE READ_REG
    set type [expr {$BRAM_MODE eq "ROM" ? "Single_Port_ROM" : "Single_Port_RAM"}]
    create_ip -name blk_mem_gen -vendor xilinx.com -library ip -version 8.4 -module_name $name
    set_property -dict [list \
        CONFIG.Memory_Type $type \
        CONFIG.Write_Width_A {16} CONFIG.Read_Width_A {16} CONFIG.Write_Depth_A $depth \
        CONFIG.Enable_A $ena \
        CONFIG.Register_PortA_Output_of_Memory_Primitives [expr {$READ_REG ? "true" : "false"}] \
        CONFIG.Load_Init_File {true} CONFIG.Coe_File $coe] [get_ips $name]
}
make_mem win_bram   400   $root/mem/win_bram.coe   {Use_ENA_Pin}
make_mem w_bram     10000 $root/mem/w_bram.coe     {Use_ENA_Pin}
make_mem bias_bram  100   $root/mem/bias_bram.coe  {Use_ENA_Pin}
# input sequence: 64 steps x 4 inputs. Use input_bram_B0018_cycle115.coe for the real-sequence (Run A) check.
make_mem input_bram 256   $root/mem/input_bram_B0018_cycle115.coe {Always_Enabled}

create_ip -name blk_mem_gen -vendor xilinx.com -library ip -version 8.4 -module_name state_bram
set_property -dict [list \
    CONFIG.Memory_Type {Simple_Dual_Port_RAM} \
    CONFIG.Write_Width_A {16} CONFIG.Read_Width_A {16} CONFIG.Write_Depth_A {100} \
    CONFIG.Write_Width_B {16} CONFIG.Read_Width_B {16} \
    CONFIG.Enable_A {Use_ENA_Pin} CONFIG.Enable_B {Use_ENB_Pin} \
    CONFIG.Register_PortB_Output_of_Memory_Primitives [expr {$READ_REG ? "true" : "false"}] \
    CONFIG.Load_Init_File {true} CONFIG.Coe_File $root/mem/state_bram.coe] [get_ips state_bram]

foreach ip {win_bram w_bram bias_bram input_bram state_bram} {
    generate_target all [get_ips $ip]
    create_ip_run [get_ips $ip]
}

# ---- simulation ----
add_files -fileset sim_1 $root/tb/tb_esn_top.v
add_files -fileset sim_1 $root/mem/tanh.mem
set_property top tb_esn_top [get_filesets sim_1]
update_compile_order -fileset sources_1
update_compile_order -fileset sim_1
puts "ESN project ready: $root/vivado_esn/ESN_FPGA.xpr"
