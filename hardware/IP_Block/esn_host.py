#!/usr/bin/env python3
"""
esn_host.py -- feed NEW battery data to the FPGA platform; ESN + EKF + UKF run on the chip at the same time.

  python esn_host.py run --pack pack_B0018 --data newcell.csv --port COM3
  python esn_host.py run --pack pack_B0018 --data B0018.mat --cycle 115 --port COM3
  # no board? emit the exact UART byte stream for the Verilator/XSim testbench, then check its reply:
  python esn_host.py run --pack pack_B0018 --data newcell.csv --emit simdir
  python esn_host.py run --pack pack_B0018 --data newcell.csv --replay simdir/resp.txt

What it does
  1. loads the model pack (ESN weights, readout weights, EKF/UKF tables) onto the FPGA (UART, once)
  2. splits the data into windows (one discharge cycle = one 64-step window), resamples each to 64 steps
  3. per window: loads EKF/UKF constants, clears the ESN, then sends one STEP frame per sample
  4. receives SOC (ESN, EKF, UKF), SOH (ESN, end of window) and measured cycle counts
  5. runs a bit-exact software twin and reports whether the chip agrees; if the data has true SOC/SOH it
     reports MAE/RMSE per estimator. Writes a CSV and (if matplotlib is present) a PNG.

Accepted data
  * CSV with columns (case-insensitive aliases): time, voltage_measured|voltage, current_measured|current,
    temperature_measured|temperature, current_load (optional, defaults to |current|),
    cycle|cycle_num (optional: one window per value), soc (optional truth), capacity (optional, Ah)
  * NASA PCoE .mat (needs scipy): use --cycle N for the N-th discharge cycle, or --cycle all
Current sign: discharge current negative (NASA convention), as the EKF/UKF models were fitted.
"""
import sys, os, json, argparse, time, csv, struct
import numpy as np
H = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [H, H + "/golden"]
from esn_frames import *
import ekf_fixed, ukf_fixed
from esn_fast import FastESN

N_STEPS = 64
rdmem = lambda p: [int(x, 16) for x in open(p).read().split()]
s32 = lambda v: v - (1 << 32) if v >> 31 else v
s16 = lambda v: v - (1 << 16) if v >> 15 else v
s18 = lambda v: v - (1 << 18) if v >> 17 else v

# ---------------------------------------------------------------- data
ALIAS = dict(time=["time", "t"], voltage_measured=["voltage_measured", "voltage", "v"],
             current_measured=["current_measured", "current", "i"], temperature_measured=["temperature_measured", "temperature", "temp"],
             current_load=["current_load", "load_current"], cycle=["cycle", "cycle_num", "cycle_id"],
             soc=["soc", "soc_true"], capacity=["capacity"])

def load_csv(path):
    rows = list(csv.reader(open(path, newline="")))
    hdr = [h.strip().lower() for h in rows[0]]
    col = {}
    for k, names in ALIAS.items():
        for n in names:
            if n in hdr: col[k] = hdr.index(n); break
    for k in ("time", "voltage_measured", "current_measured", "temperature_measured"):
        if k not in col: raise SystemExit(f"{path}: missing column '{k}' (accepted: {ALIAS[k]})")
    data = {k: np.array([float(r[i]) for r in rows[1:] if r], float) for k, i in col.items()}
    if "current_load" not in data: data["current_load"] = np.abs(data["current_measured"])
    return data

def split_windows(data, only=None):
    if "cycle" not in data: return [("all", data)]
    out = []
    for c in dict.fromkeys(data["cycle"].tolist()):
        if only not in (None, "all") and int(c) != int(only): continue
        m = data["cycle"] == c
        out.append((int(c), {k: v[m] for k, v in data.items()}))
    return out

def load_mat(path, cycle):
    import scipy.io as sio
    name = os.path.splitext(os.path.basename(path))[0]
    mat = sio.loadmat(path, struct_as_record=False, squeeze_me=True)[name].cycle
    dis = [c for c in mat if c.type == "discharge"]
    first = float(dis[0].data.Capacity)
    idx = range(len(dis)) if cycle in (None, "all") else [int(cycle)]
    out = []
    for k in idx:
        d = dis[k].data
        g = lambda a: np.atleast_1d(a).astype(float)
        t, i = g(d.Time), g(d.Current_measured); cap = float(d.Capacity)
        q = np.concatenate([[0], np.cumsum((np.abs(i[1:]) + np.abs(i[:-1])) / 2 * np.diff(t))]) / 3600
        out.append((k, dict(time=t, voltage_measured=g(d.Voltage_measured), current_measured=i,
                            temperature_measured=g(d.Temperature_measured), current_load=g(d.Current_load),
                            soc=1 - q / cap, capacity=np.full(len(t), cap), first_capacity=first)))
    return out

def resample(a, n=N_STEPS):
    a = np.asarray(a, float)
    return a if len(a) == n else np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(a)), a)

def make_window(win, soc0_arg):
    t = win["time"]; dur = float(t[-1] - t[0])
    if len(t) < 8 or dur <= 0: raise SystemExit("window too short / time not increasing")
    w = {k: resample(win[k]) for k in ("voltage_measured", "current_measured", "temperature_measured", "current_load")}
    w["dt"] = dur / (N_STEPS - 1)
    w["soc_true"] = resample(win["soc"]) if "soc" in win else None
    w["capacity"] = float(win["capacity"][0]) if "capacity" in win else None
    w["first_capacity"] = float(win["first_capacity"]) if "first_capacity" in win else None
    if soc0_arg == "true":
        if w["soc_true"] is None: raise SystemExit("--soc0 true needs a soc column")
        w["soc0"] = float(np.clip(w["soc_true"][0], 0, 1))
    else: w["soc0"] = float(soc0_arg)
    return w

# ---------------------------------------------------------------- model pack + software twin
class Pack:
    def __init__(self, d):
        self.d = d; self.j = json.load(open(d + "/pack.json"))
        self.mn = np.array([self.j["scaler_min"][k] for k in self.j["features"]])
        self.mx = np.array([self.j["scaler_max"][k] for k in self.j["features"]])
        self.win = rdmem(d + "/win_bram.mem"); self.w = rdmem(d + "/w_bram.mem"); self.bias = rdmem(d + "/bias_bram.mem")
        self.ro_soc = [s18(v) for v in rdmem(d + "/readout_soc.mem")]; self.ro_soh = [s18(v) for v in rdmem(d + "/readout_soh.mem")]
        self.luts = {n: rdmem(f"{d}/{n}.mem") for n in ("ekf_ocv", "ekf_slope", "ukf_ocv", "ukf_slope")}
        self.params = dict(ocv_poly=np.poly1d(self.j["ocv_poly"]), r0=self.j["r0"], r1=self.j["r1"], c1=self.j["c1"])
        self.nres = self.j["n_res"]; self.nin = self.j["n_in"]
        tanh = rdmem(d + "/tanh.mem")
        self.esn = FastESN(np.array([s16(v) for v in self.win], np.int64).reshape(self.nres, self.nin),
                           np.array([s16(v) for v in self.w], np.int64).reshape(self.nres, self.nres),
                           np.array([s16(v) for v in self.bias], np.int64), tanh)
    def quantise_inputs(self, w):
        X = np.stack([w[k] for k in self.j["features"]], 1)
        U = np.round((X - self.mn) / (self.mx - self.mn) * self.j["input_scale"]).astype(np.int64)
        over = int(np.sum((U > 32767) | (U < -32768)))
        return np.clip(U, -32768, 32767), over

def twin_window(pack, w, cap):
    """Bit-exact software model of one window (what the chip must reproduce)."""
    U, over = pack.quantise_inputs(w)
    pack.esn.reset(); sat16 = lambda v: int(max(-32768, min(32767, v)))
    ws, wh = np.array(pack.ro_soc[:-1], np.int64), np.array(pack.ro_soh[:-1], np.int64)
    soc, acc_h = [], 0
    for t in range(N_STEPS):
        x = pack.esn.step(U[t]).copy()
        soc.append(sat16(((int(ws @ x) + 512) >> 10) + pack.ro_soc[-1])); acc_h += int(wh @ x)
    soh = sat16(((acc_h + (1 << 15)) >> 16) + pack.ro_soh[-1])
    rows = [dict(current_measured=w["current_measured"][t], voltage_measured=w["voltage_measured"][t],
                 soc_true=w["soc0"]) for t in range(N_STEPS)]
    ekf = ekf_fixed.run_ekf_fixed(rows, ekf_fixed.build_consts(pack.params, cap, w["dt"]),
                                  [s32(v) for v in pack.luts["ekf_ocv"]], [s32(v) for v in pack.luts["ekf_slope"]])
    c = ukf_fixed.build_consts(pack.params, cap, w["dt"])
    ukf = ukf_fixed.run_ukf_fixed(rows, c, ([s32(v) for v in pack.luts["ukf_ocv"]], [s32(v) for v in pack.luts["ukf_slope"]]))
    return dict(U=U, over=over, soc_esn=np.array(soc), soh=soh, soc_ekf=ekf, soc_ukf=ukf)

def window_regs(pack, w, cap):
    """Register images for the chip's EKF and UKF (same constants the golden models use)."""
    ce = ekf_fixed.build_consts(pack.params, cap, w["dt"]); q = ekf_fixed.q; F30 = 30
    ekf = [(22, ce["a"]), (23, ce["b"]), (24, ce["kcc"]), (25, ce["r0"]), (26, ce["q0"]), (27, ce["q1"]), (28, ce["r"]),
           (31, ce["p0"]), (0, q(w["soc0"], F30))]
    cu = ukf_fixed.build_consts(pack.params, cap, w["dt"]); R = ukf_fixed.R
    d = dict(cu); d.update(X0=q(w["soc0"], F30), V1=0, P00=cu["P0"], P01=0, P11=cu["P0"])
    return ekf, [(R[k], v) for k, v in d.items()]

# ---------------------------------------------------------------- transports
class Serial:
    def __init__(self, port, baud):
        import serial
        self.s = serial.Serial(port, baud, timeout=5); self.s.reset_input_buffer()
    def exchange(self, fr, expect=None):
        self.s.write(fr)
        buf = self.s.read(4)
        if len(buf) < 4 or buf[0] != SYNC: raise IOError("no/invalid reply (check COM port, baud, bitstream)")
        ln = buf[2] | (buf[3] << 8); rest = self.s.read(ln + 1)
        if len(rest) < ln + 1: raise IOError("short reply")
        fr_ = parse_stream(buf + rest)[0]
        return fr_
class Emit:
    def __init__(self): self.frames = []
    def exchange(self, fr, expect=None): self.frames.append(fr); return (0x81, b"\0") if expect != 0x83 and expect != 0x84 else (expect, None)
class Replay:
    def __init__(self, path): self.r = iter(parse_stream(bytes(int(x, 16) for x in open(path).read().split())))
    def exchange(self, fr, expect=None): return next(self.r)

def send_write(tp, target, start, words, chunk=256):
    for f in write_frames(target, start, words, chunk):
        cmd, pl = tp.exchange(f, 0x81)
        if cmd != 0x81 or pl[0] != 0: raise IOError(f"WRITE target {target} failed: reply {cmd:#x} {pl}")

def load_pack(tp, pack):
    t0 = time.time()
    send_write(tp, T_WIN, 0, pack.win); send_write(tp, T_W, 0, pack.w); send_write(tp, T_BIAS, 0, pack.bias)
    send_write(tp, T_RO_SOC, 0, pack.ro_soc, 64); send_write(tp, T_RO_SOH, 0, pack.ro_soh, 64)
    for t, n in [(T_EKF_OCV, "ekf_ocv"), (T_EKF_SLOPE, "ekf_slope"), (T_UKF_OCV, "ukf_ocv"), (T_UKF_SLOPE, "ukf_slope")]:
        send_write(tp, t, 0, [s32(v) for v in pack.luts[n]], 200)
    return time.time() - t0

def run_window(tp, pack, w, cap):
    ekf, ukf = window_regs(pack, w, cap)
    for a, v in ekf: send_write(tp, T_EKF_REG, a, [v])
    for a, v in ukf: send_write(tp, T_UKF_REG, a, [v])
    cmd, pl = tp.exchange(ctrl_frame(True, True), 0x81)
    if cmd != 0x81 or pl[0] != 0: raise IOError("CTRL failed")
    U, _ = pack.quantise_inputs(w); out = []
    for t in range(N_STEPS):
        fr = step_frame(U[t], ekf_fixed.q(w["current_measured"][t], 28), ekf_fixed.q(w["voltage_measured"][t], 28))
        cmd, pl = tp.exchange(fr, 0x83)
        out.append(None if pl is None else decode_step(pl))
    return out

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["run", "ping"]); ap.add_argument("--pack", default=H + "/pack_B0018")
    ap.add_argument("--data"); ap.add_argument("--cycle", default=None, help="cycle number, or 'all'")
    ap.add_argument("--port"); ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--emit", help="dir: write frames.mem/flens.mem for the simulation testbench"); ap.add_argument("--replay", help="resp.txt from the testbench")
    ap.add_argument("--cap", type=float, help="rated capacity in Ah for EKF/UKF (default: file 'capacity' column, else pack)")
    ap.add_argument("--soc0", default="1.0", help="initial SOC for EKF/UKF: a number in 0..1 or 'true' (needs soc column)")
    ap.add_argument("--skip-load", action="store_true", help="pack already on the chip"); ap.add_argument("--out", default="esn_run")
    a = ap.parse_args()
    pack = Pack(a.pack)
    if a.port: tp = Serial(a.port, a.baud)
    elif a.emit: tp = Emit()
    elif a.replay: tp = Replay(a.replay)
    else: raise SystemExit("give --port COMx, or --emit DIR / --replay resp.txt for the simulation flow")
    if a.cmd == "ping":
        cmd, pl = tp.exchange(ping_frame(), 0x84); print("PING:", pl.hex() if pl else None); return
    if not a.data: raise SystemExit("--data required")
    wins = (load_mat(a.data, a.cycle) if a.data.lower().endswith(".mat") else split_windows(load_csv(a.data), a.cycle))
    if not wins: raise SystemExit("no windows found (check --cycle)")
    tp.exchange(ping_frame(), 0x84)
    cap_file = next((float(win["capacity"][0]) for _, win in wins if "capacity" in win), None)
    first_cap = next((float(win["first_capacity"]) for _, win in wins if "first_capacity" in win), cap_file)
    if not a.skip_load:
        dt_load = load_pack(tp, pack); print(f"model pack loaded in {dt_load:.1f} s" if a.port else "model pack frames queued")
    results, sim_rec = [], []
    for name, win in wins:
        w = make_window(win, a.soc0)
        w["first_capacity"] = first_cap
        cap = a.cap or first_cap or pack.j["cap_nominal"]
        tw = twin_window(pack, w, cap)
        hw = run_window(tp, pack, w, cap)
        results.append((name, w, cap, tw, hw))
    if isinstance(tp, Emit):
        os.makedirs(a.emit, exist_ok=True)
        open(a.emit + "/frames.mem", "w").write("\n".join("%02x" % b for f in tp.frames for b in f) + "\n")
        open(a.emit + "/flens.mem", "w").write("%08x\n" % len(tp.frames) + "\n".join("%08x" % len(f) for f in tp.frames) + "\n")
        json.dump([dict(name=str(n), soc_esn=[int(v) for v in tw["soc_esn"]], soh=int(tw["soh"]),
                        soc_ekf=[int(round(v * (1 << 30))) for v in tw["soc_ekf"]], soc_ukf=[int(round(v * (1 << 30))) for v in tw["soc_ukf"]],
                        n_frames=len(tp.frames)) for n, w, cap, tw, hw in results], open(a.emit + "/twin.json", "w"))
        print(f"{len(tp.frames)} frames written to {a.emit}. Run the testbench there, then: --replay {a.emit}/resp.txt"); return
    report(results, a.out)

def metrics(est, true):
    e = np.asarray(est) - np.asarray(true)
    return float(np.mean(np.abs(e))), float(np.sqrt(np.mean(e ** 2))), float(np.max(np.abs(e)))

def report(results, out):
    allrows, bad = [], 0
    print(f"{'window':>8} {'cap Ah':>6} | {'chip==twin':>10} | ESN/EKF/UKF SOC MAE vs truth | SOH chip (true)")
    for name, w, cap, tw, hw in results:
        esn = np.array([r["soc_esn"] for r in hw]) / 16384.0
        ekf = np.array([r["soc_ekf"] for r in hw]) / 2 ** 30
        ukf = np.array([r["soc_ukf"] for r in hw]) / 2 ** 30
        soh = hw[-1]["soh"] / 16384.0 if hw[-1]["soh_valid"] else float("nan")
        ok = (all(r["soc_esn"] & 0xffff == int(v) & 0xffff for r, v in zip(hw, tw["soc_esn"])) and
              all(r["soc_ekf"] == int(round(v * 2 ** 30)) for r, v in zip(hw, tw["soc_ekf"])) and
              all(r["soc_ukf"] == int(round(v * 2 ** 30)) for r, v in zip(hw, tw["soc_ukf"])) and
              hw[-1]["soh"] & 0xffff == int(tw["soh"]) & 0xffff)
        bad += (not ok)
        s = f"{str(name):>8} {cap:6.3f} | {'BIT-EXACT' if ok else 'MISMATCH':>10} | "
        if w["soc_true"] is not None:
            s += " / ".join(f"{metrics(x, w['soc_true'])[0]:.4f}" for x in (esn, ekf, ukf))
        else: s += "(no truth column)"
        sohtrue = (w["capacity"] / w["first_capacity"]) if w["capacity"] and w["first_capacity"] else None
        s += f" | {soh:.4f}" + (f" ({sohtrue:.4f})" if sohtrue else "")
        if tw["over"]: s += f"  [warning: {tw['over']} input values outside Q6.10 range]"
        print(s)
        for t, r in enumerate(hw):
            allrows.append([name, t, esn[t], ekf[t], ukf[t], "" if w["soc_true"] is None else w["soc_true"][t], r["cyc_esn"], r["cyc_ekf"], r["cyc_ukf"], r["ovf"]])
    with open(out + ".csv", "w", newline="") as f:
        cw = csv.writer(f); cw.writerow(["window", "step", "soc_esn", "soc_ekf", "soc_ukf", "soc_true", "cycles_esn", "cycles_ekf", "cycles_ukf", "esn_ovf"]); cw.writerows(allrows)
    cyc = {(r[6], r[7], r[8]) for r in allrows}
    print("measured clock cycles per sample (ESN, EKF, UKF):", sorted(cyc)[:3], "| results ->", out + ".csv")
    print("CHIP MATCHES BIT-EXACT SOFTWARE TWIN" if not bad else f"WARNING: {bad} window(s) differ from the software twin")
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, len(results), figsize=(4.5 * len(results), 3.4), squeeze=False)
        for k, (name, w, cap, tw, hw) in enumerate(results):
            A = ax[0][k]; A.plot([r["soc_esn"] / 16384 for r in hw], label="ESN"); A.plot([r["soc_ekf"] / 2 ** 30 for r in hw], label="EKF")
            A.plot([r["soc_ukf"] / 2 ** 30 for r in hw], label="UKF")
            if w["soc_true"] is not None: A.plot(w["soc_true"], "k--", label="true")
            A.set_title(f"window {name}"); A.set_xlabel("step"); A.set_ylabel("SOC")
        ax[0][0].legend(); fig.tight_layout(); fig.savefig(out + ".png", dpi=130)
    except Exception as e: print("(no plot:", e, ")")

if __name__ == "__main__": main()
