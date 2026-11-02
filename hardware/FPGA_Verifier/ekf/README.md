# Fixed-point EKF core (ekf_core) — step 1

Separate module from the ESN. The verified ESN RTL is not touched.

## Files
| File | What it is |
|---|---|
| `ekf_fixed.py` | Bit-exact golden model (integer operations, same order as the RTL) |
| `compare_ekf.py` | Float EKF (paper baseline) vs fixed-point EKF on all 4 nested-LOCO folds |
| `gen_vectors.py` | Writes `stim.mem`, `ocv_lut.mem`, `slope_lut.mem`, `golden_ekf_trace.csv` for one fold |
| `compare_rtl.py` | Compares the XSim trace with the golden trace, field by field |
| `rtl/ekf_core.v` | EKF core: one 32x32 MAC, FSM micro-program, 2 LUT ROMs, sequential divider |
| `rtl/tb_ekf_core.v` | Testbench: 8 real cycles x 64 steps (B0018 held out), dumps every register |
| `sim/` | Ready-made vectors for B0018 (`python3 gen_vectors.py <cell>` for another fold) |

## Run in Vivado (XSim)
1. Add `rtl/ekf_core.v` as a design source and `rtl/tb_ekf_core.v` as a simulation source.
2. Add `sim/stim.mem`, `sim/ocv_lut.mem`, `sim/slope_lut.mem` to the **simulation** sources
   (Add Sources -> simulation sources). Without this XSim cannot find them — same issue as `tanh_.mem`.
3. Set `tb_ekf_core` as simulation top, Run Behavioral Simulation, then `run all`.
4. The console prints the average clock cycles per step. The trace is written to
   `<project>.sim/sim_1/behav/xsim/rtl_ekf_trace.csv`.
5. `python3 compare_rtl.py sim/golden_ekf_trace.csv <path>/rtl_ekf_trace.csv`
   -> expect `ALL STAGES BIT-EXACT` over 512 steps x 22 fields.

## Synthesis numbers (after the simulation passes)
Synthesize `ekf_core` out of context (it has ~75 I/O pins, more than the board needs):
```tcl
synth_design -top ekf_core -part xc7a100tcsg324-1 -mode out_of_context
create_clock -period 12.500 -name clk [get_ports clk]
opt_design; place_design; route_design
report_utilization -hierarchical -file ekf_util.rpt
report_timing_summary -file ekf_timing.rpt
report_power -file ekf_power.rpt
```
Put `ocv_lut.mem` and `slope_lut.mem` in the design sources too, so synthesis loads the ROMs.
