#!/usr/bin/env python3
"""
narma_board.py -- NARMA-10 on the unchanged ESN platform bitstream (second application of the ESN IP).

Only weights change: Win, W, bias and the readout are written over UART at run time; the battery
pack is not needed. The script streams the NARMA-10 test sequence (200 washout + 2000 test steps),
checks every ESN output against the bit-exact software twin, and reports NRMSE.

  python narma_board.py --pack packs/narma10_task_reservoir --port COM5
  python narma_board.py --pack packs/narma10_battery_reservoir --port COM5     # deployed battery reservoir, new readout only
  python narma_board.py --pack packs/narma10_task_reservoir                    # no board: twin only

Run from esn_ip_platform/host (needs esn_host.py, esn_frames.py, golden/esn_fast.py).
"""
import os, sys, argparse, time
import numpy as np
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, H + "/golden", os.path.join(H, "..")]
from esn_frames import *
from esn_fast import FastESN
import esn_host as eh

WASH = 200


def rd16(p): return np.array([eh.s16(v) for v in eh.rdmem(p)], np.int64)
def rd18(p): return np.array([eh.s18(v) for v in eh.rdmem(p)], np.int64)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pack", required=True); ap.add_argument("--port"); ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--skip-load", action="store_true")
    a = ap.parse_args(); d = a.pack
    Win, W, b = rd16(d + "/win_bram.mem"), rd16(d + "/w_bram.mem"), rd16(d + "/bias_bram.mem")
    q = rd18(d + "/readout_soc.mem"); n = len(b)
    tanh_path = d + "/tanh.mem" if os.path.exists(d + "/tanh.mem") else H + "/packs/general_32cells/tanh.mem"
    u = np.loadtxt(d + "/narma_test_u.txt"); y = np.loadtxt(d + "/narma_test_y.txt")
    U = np.zeros((len(u), 4), np.int64); U[:, 1] = np.clip(np.round(u * 1024), -32768, 32767)   # input on channel 1, as trained

    esn = FastESN(Win.reshape(n, 4), W.reshape(n, n), b, eh.rdmem(tanh_path))
    twin = []
    for t in range(len(U)):
        x = esn.step(U[t]); twin.append(int(np.clip(((int(q[:-1] @ x) + 512) >> 10) + q[-1], -32768, 32767)))
    twin = np.array(twin)
    nrmse = lambda yh: float(np.sqrt(np.mean((yh[WASH:] - y[WASH:]) ** 2) / np.var(y[WASH:])))
    print(f"pack {d}: N_RES {n}, {len(U)} steps ({WASH} washout)")
    print(f"software twin NRMSE {nrmse(twin / 16384.0):.4f}")
    if not a.port: return

    tp = eh.Serial(a.port, a.baud)
    cmd, pl = tp.exchange(ping_frame(), 0x84); print("PING", pl.hex())
    if not a.skip_load:
        t0 = time.time()
        eh.send_write(tp, T_WIN, 0, Win.tolist()); eh.send_write(tp, T_W, 0, W.tolist()); eh.send_write(tp, T_BIAS, 0, b.tolist())
        eh.send_write(tp, T_RO_SOC, 0, q.tolist(), 64); eh.send_write(tp, T_RO_SOH, 0, [0] * (n + 1), 64)
        print(f"weights loaded in {time.time() - t0:.1f} s")
    cmd, pl = tp.exchange(ctrl_frame(True, True), 0x81)
    if cmd != 0x81 or pl[0] != 0: raise IOError("CTRL failed")
    chip, cyc, ovf = [], set(), 0
    t0 = time.time()
    for t in range(len(U)):
        cmd, pl = tp.exchange(step_frame(U[t], 0, 0), 0x83); r = decode_step(pl)
        chip.append(r["soc_esn"]); cyc.add(r["cyc_esn"]); ovf |= r["ovf"]
    chip = np.array(chip)
    bad = int(np.sum((chip & 0xffff) != (twin & 0xffff)))
    print(f"{len(U)} steps in {time.time() - t0:.1f} s | chip vs twin mismatches: {bad} | MAC overflow seen: {ovf} | ESN cycles/step: {sorted(cyc)}")
    print(f"chip NRMSE {nrmse(chip / 16384.0):.4f}")
    print("CHIP MATCHES BIT-EXACT SOFTWARE TWIN" if bad == 0 else "WARNING: chip differs from the twin")
    np.savetxt("narma_board_out.csv", np.c_[np.arange(len(U)), u, y, chip / 16384.0, twin / 16384.0], delimiter=",",
               header="step,u,y_true,y_chip,y_twin", comments="")


if __name__ == "__main__":
    main()
