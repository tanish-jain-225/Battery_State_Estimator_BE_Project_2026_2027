#!/usr/bin/env python3
"""
real_nasa_dataset.py
─────────────────────
Replaces the synthetic `generate_nasa_battery_dataset()` formerly in
eval_fpga_outcomes.py. Loads the ACTUAL NASA PCoE battery .mat files
(B0005, B0006, B0007, B0018) and extracts real voltage/current/
temperature/load-current telemetry, real Coulomb-counted SOC, and real
capacity-fade SOH -- nothing here is synthesized.

Matches the project's documented methodology:
  - 8 discharge cycles per battery, chosen to span each battery's SOH range
  - Each cycle resampled to 64 evenly-spaced timesteps (the raw NASA
    discharge traces have irregular, non-64 sample counts per cycle; the
    FPGA's input_bram is sized for T_MAX=64, so resampling -- not
    truncation -- is required to use every cycle's full discharge span)
  - Features: voltage_measured, current_measured, temperature_measured,
    current_load (matches N_IN=4 and the committed win_bram.coe layout)
  - SOC: within-cycle Coulomb counting against that cycle's own measured
    discharge capacity
  - SOH: that cycle's capacity relative to the battery's FIRST discharge
    cycle capacity
  - Train: B0005 only. Test: B0006, B0007, B0018 (unseen).

Requires the four .mat files to be present in MAT_DIR.
"""

import os
import numpy as np
import scipy.io as sio

MAT_DIR = os.environ.get("NASA_MAT_DIR", "/mnt/user-data/uploads")

BATTERY_CYCLES = {
    "B0005": {"role": "Train", "cycles": [0, 28, 56, 84, 105, 126, 146, 167]},
    "B0006": {"role": "Test",  "cycles": [0, 28, 56, 83, 105, 126, 146, 167]},
    "B0007": {"role": "Test",  "cycles": [0, 28, 56, 83, 105, 126, 146, 167]},
    "B0018": {"role": "Test",  "cycles": [0, 22, 44, 65, 82, 98, 115, 131]},
}

N_TIMESTEPS = 64
FEATURE_KEYS = ["voltage_measured", "current_measured", "temperature_measured", "current_load"]


def _compute_soc(time_arr, current_arr, capacity_ah):
    """Within-cycle Coulomb counting against measured discharge capacity."""
    time_arr = np.asarray(time_arr, dtype=float)
    current_arr = np.abs(np.asarray(current_arr, dtype=float))
    charge_removed_as = np.zeros(len(time_arr))
    for i in range(1, len(time_arr)):
        dt = time_arr[i] - time_arr[i - 1]
        avg_i = (current_arr[i] + current_arr[i - 1]) / 2.0
        charge_removed_as[i] = charge_removed_as[i - 1] + avg_i * dt
    charge_removed_ah = charge_removed_as / 3600.0
    return 1.0 - (charge_removed_ah / capacity_ah)


def _resample(arr, n_out):
    """Linearly resample a 1-D array to exactly n_out points (not truncation)."""
    arr = np.asarray(arr, dtype=float)
    if len(arr) == n_out:
        return arr
    x_src = np.linspace(0.0, 1.0, len(arr))
    x_dst = np.linspace(0.0, 1.0, n_out)
    return np.interp(x_dst, x_src, arr)


def generate_nasa_battery_dataset(mat_dir=None, n_timesteps=N_TIMESTEPS):
    """
    Loads the REAL NASA .mat files and returns
    (raw_data: list[dict], batteries_meta: dict) in the same shape the
    rest of eval_fpga_outcomes.py expects, so downstream code is unchanged.
    Each row carries true (not fabricated) telemetry and labels.
    """
    mat_dir = mat_dir or MAT_DIR
    raw_data = []
    batteries_meta = {}

    for b_id, info in BATTERY_CYCLES.items():
        mat_path = os.path.join(mat_dir, f"{b_id}.mat")
        if not os.path.exists(mat_path):
            raise FileNotFoundError(
                f"Required NASA .mat file not found: {mat_path}. "
                f"Set NASA_MAT_DIR or place {b_id}.mat in {mat_dir}."
            )
        mat = sio.loadmat(mat_path, struct_as_record=False, squeeze_me=True)
        all_cycles = mat[b_id].cycle
        discharge_cycles = [c for c in all_cycles if c.type == "discharge"]

        first_cap = float(discharge_cycles[0].data.Capacity)
        cap_values = []

        for cycle_num in info["cycles"]:
            if cycle_num >= len(discharge_cycles):
                raise IndexError(
                    f"{b_id}: requested discharge cycle index {cycle_num}, "
                    f"but only {len(discharge_cycles)} discharge cycles exist."
                )
            c = discharge_cycles[cycle_num]
            d = c.data

            time_arr = np.atleast_1d(d.Time).astype(float)
            v_meas = np.atleast_1d(d.Voltage_measured).astype(float)
            i_meas = np.atleast_1d(d.Current_measured).astype(float)
            t_meas = np.atleast_1d(d.Temperature_measured).astype(float)
            i_load = np.atleast_1d(d.Current_load).astype(float)
            capacity = float(d.Capacity)
            cap_values.append(capacity)

            soc_full = _compute_soc(time_arr, i_meas, capacity)
            soh = capacity / first_cap

            # Resample every channel (and the SOC trace itself) to exactly
            # n_timesteps points spanning the cycle's real discharge span --
            # this is a resampling of real measured data, not fabrication.
            v_rs = _resample(v_meas, n_timesteps)
            i_rs = _resample(i_meas, n_timesteps)
            t_rs = _resample(t_meas, n_timesteps)
            il_rs = _resample(i_load, n_timesteps)
            soc_rs = _resample(soc_full, n_timesteps)

            # Real per-step time delta for THIS cycle after resampling to
            # n_timesteps points -- needed by any physics-based estimator
            # (e.g. the EKF baseline) that integrates current over dt.
            # Resampling changes the sample spacing, so dt must be
            # recomputed here rather than assumed to be the raw dataset's
            # native ~1s sampling interval.
            cycle_duration_s = float(time_arr[-1] - time_arr[0])
            dt_resampled = cycle_duration_s / (n_timesteps - 1) if n_timesteps > 1 else cycle_duration_s

            for t_i in range(n_timesteps):
                raw_data.append({
                    "battery": b_id,
                    "role": info["role"],
                    "cycle": cycle_num,
                    "timestep": t_i,
                    "voltage_measured": float(v_rs[t_i]),
                    "current_measured": float(i_rs[t_i]),
                    "temperature_measured": float(t_rs[t_i]),
                    "current_load": float(il_rs[t_i]),
                    "soc_true": float(np.clip(soc_rs[t_i], 0.0, 1.0)),
                    "soh_true": float(soh),
                    "dt": dt_resampled,
                })

        batteries_meta[b_id] = {
            "role": info["role"],
            "cycles": info["cycles"],
            "soh_range": (1.0, cap_values[-1] / first_cap),
            "cap_nominal": first_cap,
        }

    return raw_data, batteries_meta


if __name__ == "__main__":
    data, meta = generate_nasa_battery_dataset()
    print(f"Loaded {len(data)} rows from REAL NASA .mat files across "
          f"{len(meta)} batteries ({sum(len(v['cycles']) for v in meta.values())} cycles).")
    for b, m in meta.items():
        print(f"  {b}: role={m['role']}, cycles={m['cycles']}, "
              f"SOH range={m['soh_range'][0]:.4f}->{m['soh_range'][1]:.4f}, "
              f"first-cycle capacity={m['cap_nominal']:.4f} Ah")
