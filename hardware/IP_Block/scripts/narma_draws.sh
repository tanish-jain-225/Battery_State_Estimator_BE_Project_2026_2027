#!/bin/bash
# RTL replay of the ten further NARMA-10 reservoir draws (test_data/sim_narma10_draw100..109)
#   bash scripts/narma_draws.sh                     -> reference core
#   CORE_ARGS="-GFAST=1 -GP=10 -GK=24" bash ...     -> fast core
set -e
ROOT=$(cd $(dirname $0)/.. && pwd); W=${WORK:-$ROOT/_draws}; mkdir -p $W/build
RTL=$ROOT/rtl
CORE="$RTL/esn_core.v $RTL/esn_core_fast.v $RTL/esn_ram.v $RTL/esn_readout.v $RTL/esn_neuron.v $RTL/mac_accum_q6_10.v $RTL/mult_q6_10.v $RTL/tanh_lut.v $RTL/reservoir_controller.v $RTL/address_generator.v"
PLAT="$RTL/esn_platform.v $CORE $RTL/ekf_core.v $RTL/ukf_core.v $RTL/uart_rx.v $RTL/uart_tx.v"
cd $W/build; verilator --binary --timing -Wno-fatal -Wno-lint -j 8 ${CORE_ARGS} --top-module tb_esn_platform -o sim $ROOT/tb/tb_esn_platform.v $PLAT > vl.log 2>&1
for S in 100 101 102 103 104 105 106 107 108 109; do
  T=sim_narma10_draw$S; D=$W/$T; rm -rf $D; mkdir -p $D; cp $ROOT/test_data/$T/*.mem $ROOT/mem/tanh.mem $D/; cd $D
  $W/build/obj_dir/sim > run.log 2>&1
  python3 - $ROOT $T <<'P'
import sys,json
root,T=sys.argv[1:3]; sys.path[:0]=[root+"/host"]
from esn_frames import *
fr=parse_stream(bytes(int(x,16) for x in open("resp.txt").read().split()))
st=[decode_step(p) for c,p in fr if c==0x83]; tw=json.load(open(root+"/test_data/"+T+"/twin.json"))
bad=sum((r["soc_esn"]&0xffff)!=(v&0xffff) for r,v in zip(st,tw["soc_esn"]))+abs(len(st)-tw["nsteps"])
print(("PASS" if not bad else "FAIL"),T,":",len(st),"steps, mismatches =",bad,"| cycles/step",sorted({r["cyc_esn"] for r in st}))
P
done
