#!/usr/bin/env python3
"""
replay_board.py -- send a recorded test-vector set (test_data/<name>/frames.mem) to the platform over UART
and compare every step reply with the bit-exact twin (twin.json): ESN SOC always, EKF SOC when the twin has it.

  python replay_board.py --vec ../test_data/sim_fused_b47 --port COM5      # fused EKF + ESN, 1,732 steps
  python replay_board.py --vec ../test_data/sim_causal_b47 --port COM5     # causal ESN streaming

Needs the bitstream built from this release (ekf_core Rev 0.5 for the fused test).
Run from esn_ip_platform/host. Writes <name>_board.csv next to this script.
"""
import os, sys, json, argparse, time, csv
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H]
from esn_frames import *
import esn_host as eh


def frames_from(vec):
    data = bytes(int(x, 16) for x in open(vec + "/frames.mem").read().split())
    lens = [int(x, 16) for x in open(vec + "/flens.mem").read().split()][1:]
    out, i = [], 0
    for n in lens: out.append(data[i:i + n]); i += n
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vec", required=True); ap.add_argument("--port", required=True); ap.add_argument("--baud", type=int, default=115200)
    a = ap.parse_args()
    tw = json.load(open(a.vec + "/twin.json")); fr = frames_from(a.vec)
    tp = eh.Serial(a.port, a.baud); t0 = time.time(); steps = []
    for k, f in enumerate(fr):
        cmd, pl = tp.exchange(f)
        if f[1] == CMD_STEP:
            if cmd != 0x83: raise IOError(f"frame {k}: expected step reply, got {cmd:#x}")
            steps.append(decode_step(pl))
        elif cmd != 0x81 or pl[0] != 0:
            raise IOError(f"frame {k}: reply {cmd:#x} {list(pl)}")
    dt = time.time() - t0
    be = sum((r["soc_esn"] & 0xffff) != (v & 0xffff) for r, v in zip(steps, tw["soc_esn"]))
    bk = sum((r["soc_ekf"] & 0xffffffff) != (v & 0xffffffff) for r, v in zip(steps, tw["soc_ekf"])) if "soc_ekf" in tw else 0
    name = os.path.basename(os.path.normpath(a.vec))
    with open(os.path.join(H, name + "_board.csv"), "w", newline="") as fh:
        cw = csv.writer(fh); cw.writerow(["step", "soc_esn", "soc_ekf", "cyc_esn", "cyc_ekf", "cyc_ukf"])
        for i, r in enumerate(steps): cw.writerow([i, r["soc_esn"], r["soc_ekf"], r["cyc_esn"], r["cyc_ekf"], r["cyc_ukf"]])
    print(f"{name}: {len(steps)} steps in {dt:.1f} s (expected {tw['nsteps']})")
    print(f"  ESN mismatches vs twin: {be}" + (f" | fused EKF mismatches vs twin: {bk}" if "soc_ekf" in tw else ""))
    print(f"  cycles per step: ESN {sorted(set(r['cyc_esn'] for r in steps))[:4]}  EKF {sorted(set(r['cyc_ekf'] for r in steps))[:6]}")
    print("RESULT", "PASS" if be == 0 and bk == 0 and len(steps) == tw["nsteps"] else "FAIL")


if __name__ == "__main__":
    main()
