# sweep_fast.tcl -- out-of-context implementation of esn_axi_ip with the fast core, several (N_RES, P, K).
# Same RTL as sweep_nres.tcl; only generics change. Vivado 2023.1, XC7A100T, 80 MHz.
#   cd esn_ip_platform ; vivado -mode batch -source scripts/sweep_fast.tcl
# Writes sweep_fast/summary.csv and reports per configuration.
set root  [file normalize [file dirname [info script]]/..]
set part  xc7a100tcsg324-1
# {N_RES FAST P K}
set cfgs  {{100 1 1 24} {100 1 2 24} {100 1 4 24} {100 1 10 24} {100 1 1 100} {50 1 10 16} {200 1 10 48}}
set out   $root/sweep_fast
file mkdir $out
set csv [open $out/summary.csv w]
puts $csv "N_RES,FAST,P,K,LUT,FF,BRAM_tiles,DSP,WNS_ns,total_power_W,dynamic_power_W"
foreach c $cfgs {
    lassign $c n f p k
    set d $out/N${n}_P${p}_K${k}; file mkdir $d
    close_project -quiet
    create_project -in_memory -part $part
    read_verilog [glob $root/rtl/esn_axi_ip.v $root/rtl/esn_core.v $root/rtl/esn_core_fast.v $root/rtl/esn_readout.v \
                       $root/rtl/esn_ram.v $root/rtl/esn_neuron.v $root/rtl/mac_accum_q6_10.v $root/rtl/mult_q6_10.v \
                       $root/rtl/tanh_lut.v $root/rtl/reservoir_controller.v $root/rtl/address_generator.v]
    add_files $root/mem/tanh.mem
    synth_design -top esn_axi_ip -part $part -mode out_of_context -generic N_RES=$n -generic FAST=$f -generic P=$p -generic K=$k
    create_clock -name aclk -period 12.500 [get_ports aclk]
    opt_design; place_design; route_design
    report_utilization    -file $d/utilization.rpt
    report_timing_summary -file $d/timing.rpt
    report_power          -file $d/power.rpt
    set urs [report_utilization -return_string]
    set lut NA; set ff NA; set bram NA; set dsp NA
    regexp {Slice LUTs\s*\|\s*([0-9]+)}       $urs -> lut
    regexp {Slice Registers\s*\|\s*([0-9]+)}  $urs -> ff
    regexp {Block RAM Tile\s*\|\s*([0-9.]+)}  $urs -> bram
    regexp {DSPs\s*\|\s*([0-9]+)}             $urs -> dsp
    set wns [get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]]
    set prs [report_power -return_string]
    set pw NA; set pd NA
    regexp {Total On-Chip Power \(W\)\s*\|\s*([0-9.]+)} $prs -> pw
    regexp {Dynamic \(W\)\s*\|\s*([0-9.]+)} $prs -> pd
    puts $csv "$n,$f,$p,$k,$lut,$ff,$bram,$dsp,$wns,$pw,$pd"
    flush $csv
    puts "N=$n P=$p K=$k done: LUT $lut FF $ff BRAM $bram DSP $dsp WNS $wns P $pw"
}
close $csv
puts "Summary: $out/summary.csv"
