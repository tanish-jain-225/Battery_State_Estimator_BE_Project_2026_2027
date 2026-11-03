#!/bin/bash
# Verilator regression of the whole bundle (needs verilator >= 5 and python3 + numpy).
#   bash scripts/regression.sh            -> prints PASS/FAIL lines
set -e
ROOT=$(cd $(dirname $0)/.. && pwd); W=${WORK:-$ROOT/_regress}; mkdir -p $W
V="verilator --binary --timing -Wno-fatal -Wno-lint -j 8"
RTL=$ROOT/rtl
CORE="$RTL/esn_core.v $RTL/esn_ram.v $RTL/esn_readout.v $RTL/esn_neuron.v $RTL/mac_accum_q6_10.v $RTL/mult_q6_10.v $RTL/tanh_lut.v $RTL/reservoir_controller.v $RTL/address_generator.v"
PLAT="$RTL/esn_platform.v $CORE $RTL/ekf_core.v $RTL/ukf_core.v $RTL/uart_rx.v $RTL/uart_tx.v"

# 1) AXI IP: register mode and stream mode against the verified golden SOC trace
D=$W/axi; rm -rf $D; mkdir -p $D; cp $ROOT/verify/*.mem $ROOT/verify/*.csv $ROOT/mem/tanh.mem $D/; cd $D
$V --top-module tb_esn_axi_ip -o sim $ROOT/tb/tb_esn_axi_ip.v $RTL/esn_axi_ip.v $CORE > vl.log 2>&1; ./obj_dir/sim > run.log 2>&1
python3 - <<'P'
import csv
g=list(csv.reader(open("golden_readout.csv")))[1:]
for f in ("rtl_axil.csv","rtl_axis.csv"):
    r=list(csv.reader(open(f)))[1:]
    ok=all(int(a[1],16)==int(b[1],16) for a,b in zip(g[:64],r[:64])) and r[64][1].lower()==g[64][1].lower()
    print(("PASS" if ok else "FAIL"),"AXI IP",f,"SOC 64/64 + SOH",r[64][1])
P

# 2) platform: replay UART frame streams (ESN + EKF + UKF concurrently), compare with the bit-exact software twin
for T in sim_c115 sim_b47; do
  D=$W/$T; rm -rf $D; mkdir -p $D; cp $ROOT/test_data/$T/*.mem $ROOT/mem/tanh.mem $D/; cd $D
  $V --top-module tb_esn_platform -o sim $ROOT/tb/tb_esn_platform.v $PLAT > vl.log 2>&1; ./obj_dir/sim > run.log 2>&1
  python3 - $ROOT $T <<'P'
import sys,json,os
root,T=sys.argv[1:3]; sys.path[:0]=[root+"/host"]
from esn_frames import *
fr=parse_stream(bytes(int(x,16) for x in open("resp.txt").read().split()))
tw=json.load(open(root+"/test_data/"+T+"/twin.json")); st=[decode_step(p) for c,p in fr if c==0x83]
bad=0
for w,name in enumerate(tw):
    for t in range(64):
        r=st[w*64+t]
        bad+= (r["soc_esn"]&0xffff)!=(name["soc_esn"][t]&0xffff) or (r["soc_ekf"]&0xffffffff)!=(name["soc_ekf"][t]&0xffffffff) or (r["soc_ukf"]&0xffffffff)!=(name["soc_ukf"][t]&0xffffffff)
    bad+= (st[w*64+63]["soh"]&0xffff)!=(name["soh"]&0xffff)
print(("PASS" if not bad else "FAIL"),"platform",T,":",len(st),"steps,",len(tw),"windows, ESN+EKF+UKF+SOH mismatches =",bad,"| cycles/step",st[0]["cyc_esn"],st[0]["cyc_ekf"],st[0]["cyc_ukf"])
P
done
