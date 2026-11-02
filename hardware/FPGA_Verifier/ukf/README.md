# Fixed-point UKF core (ukf_core) — same architecture as ekf_core Rev 0.3

## Accuracy (nested LOCO, 4 NASA cells, pooled SOC)
| | MAE | RMSE | R² |
|---|---|---|---|
| EKF float | 0.0847 | 0.1013 | 0.8975 |
| UKF float | 0.0846 | 0.1012 | 0.8976 |
| UKF fixed (this core) | 0.0846 | 0.1012 | 0.8977 |
Fixed vs float UKF: max SOC difference 6.1e-4. Per-cell numbers in `compare_results.json`.

## Design
- Additive-noise UKF, Julier sigma points (kappa = 3 - n): gamma = sqrt(3), W0 = 1/3, Wi = 1/6.
- 73 micro-ops per step: 65 MAC, 3 LUT (with linear interpolation), 3 DIV, 2 SQRT.
- `ukf_fixed.py` holds the op list; `gen_ukf.py` turns the same list into `rtl/ukf_ucode.vh`,
  so golden model and RTL run the identical sequence.
- Expected ~590 clock cycles per step (~7.4 µs at 80 MHz).

## Files
| File | |
|---|---|
| `ukf_float.py`, `ukf_fixed.py` | float reference, bit-exact golden model |
| `compare_ukf.py` | EKF vs UKF float vs UKF fixed on all 4 folds |
| `gen_ukf.py` | regenerates microcode, trace include, ROMs, stimulus, golden trace |
| `rtl/ukf_core.v`, `rtl/ukf_ucode.vh` | core + micro-program (include) |
| `rtl/tb_ukf_core.v`, `rtl/ukf_trace.vh` | testbench + trace format (include) |
| `rtl/ukf_core.xdc` | 80 MHz clock, I/O false paths (same as EKF/ESN) |
| `sim/` | `ukf_stim.mem`, `ukf_ocv.mem`, `ukf_slope.mem`, `golden_ukf_trace.csv` (B0018 held out) |

## Vivado
1. Design sources: `ukf_core.v`, `ukf_ucode.vh`, `ukf_ocv.mem`, `ukf_slope.mem`.
   Simulation sources: `tb_ukf_core.v`, `ukf_trace.vh`, `ukf_stim.mem` (+ the two ROM .mem files).
   The UKF ROM files have different names from the EKF ones on purpose (different contents).
2. Simulation top `tb_ukf_core` → Run Behavioral Simulation → `run all`.
3. `python3 compare_rtl.py sim/golden_ukf_trace.csv <xsim dir>/rtl_ukf_trace.csv` → `ALL STAGES BIT-EXACT`.
4. Synthesis: top `ukf_core`, constraints `ukf_core.xdc` only (disable esn_top.xdc / ekf xdc).
