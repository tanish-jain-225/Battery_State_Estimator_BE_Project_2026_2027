#!/bin/bash
# Verilator regression of the whole bundle (needs verilator >= 5 and python3 + numpy).
#   bash scripts/regression.sh                                       -> reference core (esn_core)
#   CORE_ARGS="-GFAST=1 -GP=10 -GK=24" bash scripts/regression.sh    -> fast core, 10 lanes
# prints PASS/FAIL lines
set -e
ROOT=$(cd $(dirname $0)/.. && pwd); W=${WORK:-$ROOT/_regress}; mkdir -p $W
V="verilator --binary --timing -Wno-fatal -Wno-lint -j 8 ${CORE_ARGS}"
RTL=$ROOT/rtl
CORE="$RTL/esn_core.v $RTL/esn_core_fast.v $RTL/esn_ram.v $RTL/esn_readout.v $RTL/esn_neuron.v $RTL/mac_accum_q6_10.v $RTL/mult_q6_10.v $RTL/tanh_lut.v $RTL/reservoir_controller.v $RTL/address_generator.v"
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
# sim_c115, sim_b47: October vectors (room-temperature pack). sim_v11_general: v1.1 host + general_32cells pack,
# trimmed B0047 windows. sim_v11_b43clip: held-out B0043 pack, which has one readout weight clipped to Q4.14.
for T in sim_c115 sim_b47 sim_v11_general sim_v11_b43clip; do
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

# 3) platform: NARMA-10 (second application, new weights only) and causal battery streaming
#    (B0047, 8 sequences of 142-309 samples, full and mid-discharge starts, state cleared per sequence),
#    compared step by step with the twin
for T in sim_narma10_task sim_narma10_battery sim_causal_b47; do
  D=$W/$T; rm -rf $D; mkdir -p $D; cp $ROOT/test_data/$T/*.mem $ROOT/mem/tanh.mem $D/; cd $D
  $V --top-module tb_esn_platform -o sim $ROOT/tb/tb_esn_platform.v $PLAT > vl.log 2>&1; ./obj_dir/sim > run.log 2>&1
  python3 - $ROOT $T <<'P'
import sys,json
root,T=sys.argv[1:3]; sys.path[:0]=[root+"/host"]
from esn_frames import *
fr=parse_stream(bytes(int(x,16) for x in open("resp.txt").read().split()))
st=[decode_step(p) for c,p in fr if c==0x83]; tw=json.load(open(root+"/test_data/"+T+"/twin.json"))
bad=sum((r["soc_esn"]&0xffff)!=(v&0xffff) for r,v in zip(st,tw["soc_esn"]))+abs(len(st)-tw["nsteps"])
print(("PASS" if not bad else "FAIL"),"platform",T,":",len(st),"steps, ESN mismatches =",bad,"| cycles/step",sorted({r["cyc_esn"] for r in st}))
P
done

# 4) platform: fused EKF (ekf_core Rev 0.5, FUSE = 1): the EKF uses the ESN SOC of the same step as a second
#    measurement. B0047, 8 causal sequences, 1,732 steps; ESN and fused-EKF outputs compared with the twin.
for T in sim_fused_b47; do
  D=$W/$T; rm -rf $D; mkdir -p $D; cp $ROOT/test_data/$T/*.mem $ROOT/mem/tanh.mem $D/; cd $D
  $V --top-module tb_esn_platform -o sim $ROOT/tb/tb_esn_platform.v $PLAT > vl.log 2>&1; ./obj_dir/sim > run.log 2>&1
  python3 - $ROOT $T <<'P'
import sys,json
root,T=sys.argv[1:3]; sys.path[:0]=[root+"/host"]
from esn_frames import *
fr=parse_stream(bytes(int(x,16) for x in open("resp.txt").read().split()))
st=[decode_step(p) for c,p in fr if c==0x83]; tw=json.load(open(root+"/test_data/"+T+"/twin.json"))
be=sum((r["soc_esn"]&0xffff)!=(v&0xffff) for r,v in zip(st,tw["soc_esn"]))
bk=sum((r["soc_ekf"]&0xffffffff)!=(v&0xffffffff) for r,v in zip(st,tw["soc_ekf"]))
bad=be+bk+abs(len(st)-tw["nsteps"])
print(("PASS" if not bad else "FAIL"),"platform",T,":",len(st),"steps, ESN mismatches =",be,", fused EKF mismatches =",bk,"| cycles/step ESN",sorted({r["cyc_esn"] for r in st}),"EKF",sorted({r["cyc_ekf"] for r in st}))
P
done
