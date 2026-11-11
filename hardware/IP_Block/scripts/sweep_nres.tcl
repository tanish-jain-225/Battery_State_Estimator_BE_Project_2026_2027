# sweep_nres.tcl -- out-of-context implementation of the ESN IP (esn_axi_ip) for several reservoir sizes.
# Same RTL, only the N_RES generic changes. Vivado 2023.1, Arty A7-100T part, 80 MHz.
#
#   cd esn_ip_platform
#   vivado -mode batch -source scripts/sweep_nres.tcl
#
# Writes sweep_nres/summary.csv and full reports per size in sweep_nres/N<size>/.
set root  [file normalize [file dirname [info script]]/..]
set part  xc7a100tcsg324-1
set sizes {50 100 200}
set out   $root/sweep_nres
file mkdir $out
set csv [open $out/summary.csv w]
puts $csv "N_RES,LUT,FF,BRAM_tiles,DSP,WNS_ns,total_power_W,dynamic_power_W"

foreach n $sizes {
    set d $out/N$n; file mkdir $d
    close_project -quiet
    create_project -in_memory -part $part
    read_verilog [glob $root/rtl/esn_axi_ip.v $root/rtl/esn_core.v $root/rtl/esn_readout.v $root/rtl/esn_ram.v \
                       $root/rtl/esn_neuron.v $root/rtl/mac_accum_q6_10.v $root/rtl/mult_q6_10.v \
                       $root/rtl/tanh_lut.v $root/rtl/reservoir_controller.v $root/rtl/address_generator.v]
    add_files $root/mem/tanh.mem
    synth_design -top esn_axi_ip -part $part -mode out_of_context -generic N_RES=$n
    create_clock -name aclk -period 12.500 [get_ports aclk]
    opt_design; place_design; route_design
    report_utilization     -file $d/utilization.rpt
    report_timing_summary  -file $d/timing.rpt
    report_power           -file $d/power.rpt

    set urs  [report_utilization -return_string]
    set lut NA; set ff NA; set bram NA; set dsp NA
    regexp {Slice LUTs\s*\|\s*([0-9]+)}       $urs -> lut
    regexp {Slice Registers\s*\|\s*([0-9]+)}  $urs -> ff
    regexp {Block RAM Tile\s*\|\s*([0-9.]+)}  $urs -> bram
    regexp {DSPs\s*\|\s*([0-9]+)}             $urs -> dsp
    set wns  [get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]]
    set prs  [report_power -return_string]
    set pw NA; set pd NA
    regexp {Total On-Chip Power \(W\)\s*\|\s*([0-9.]+)} $prs -> pw
    regexp {Dynamic \(W\)\s*\|\s*([0-9.]+)} $prs -> pd
    puts $csv "$n,$lut,$ff,$bram,$dsp,$wns,$pw,$pd"
    flush $csv
    puts "N_RES=$n done: LUT $lut FF $ff BRAM $bram DSP $dsp WNS $wns"
}
close $csv
puts "Summary: $out/summary.csv  "
