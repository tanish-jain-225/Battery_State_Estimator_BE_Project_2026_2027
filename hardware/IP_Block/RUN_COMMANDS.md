# Run commands, esn_ip_platform v1.2

Every command needed to build, program, run and check the ESN IP and the board platform, in order.
Written for Windows (Command Prompt or PowerShell) with Vivado 2023.1 and the Arty A7-100T.
Replace `D:\esn_ip_platform` with your folder and `COM3` with your board's port.

## 0. One-time setup

```
:: unzip to a short path with no spaces, e.g. D:\esn_ip_platform
py -m pip install numpy scipy scikit-learn pyserial matplotlib
```
On Windows use `py`; if `py` is not found, use `python`.
Find the COM port: Device Manager > Ports (COM & LPT) > "USB Serial Port (COMx)". The Arty shows two; the UART is usually the higher number.

## 1. Build the bitstream (board platform: ESN + EKF + UKF + UART)

Fast core, 10 lanes (recommended; this is the build verified on the board):
```
cd /d D:\esn_ip_platform
vivado -mode batch -source scripts/build_platform.tcl -tclargs fast
```
Or from the Vivado Tcl console:
```
set ESN_ROOT D:/esn_ip_platform
set ESN_FAST {1 10 24}
source D:/esn_ip_platform/scripts/build_platform.tcl
```
Output: `vivado_fast\esn_platform.runs\impl_1\esn_platform_top.bit`, reports in `vivado_fast\reports\`.

Serial core (smallest area), from the Tcl console:
```
set ESN_ROOT D:/esn_ip_platform
source D:/esn_ip_platform/scripts/build_platform.tcl
```
Output: `vivado\esn_platform.runs\impl_1\esn_platform_top.bit`, reports in `vivado\reports\`.

After the build, open `reports\timing.txt` and check that WNS is 0 or positive.

## 2. Program the board

Vivado GUI: Open Hardware Manager > Open Target > Auto Connect > Program Device > select the `.bit` above > Program.
Or from the Tcl console:
```
open_hw_manager
connect_hw_server
open_hw_target
set_property PROGRAM.FILE {D:/esn_ip_platform/vivado_fast/esn_platform.runs/impl_1/esn_platform_top.bit} [current_hw_device]
program_hw_devices [current_hw_device]
```
LED LD7 on = clock locked. LD4 busy, LD5 good frame, LD6 ESN MAC overflow seen.

## 3. Talk to the board

All host commands run from the `host` folder:
```
cd /d D:\esn_ip_platform\host
py esn_host.py ping --port COM3
```
Expected answer: `N_IN 4, N_RES 100, T 64`.

## 4. Battery SOC/SOH on the board (windowed, ESN + EKF + UKF)

General pack, held-out cold cell B0047, all windows:
```
py esn_host.py run --pack packs/general_32cells --data packs/heldout/pack_B0047/B0047_cycles.csv --cycle all --port COM3
```
Held-out pack (model never saw B0047):
```
py esn_host.py run --pack packs/heldout/pack_B0047 --data packs/heldout/pack_B0047/B0047_cycles.csv --cycle all --port COM3
```
Useful options: `--skip-load` (pack already on the chip, saves about 3.5 s), `--cap 2.0` (EKF/UKF with rated capacity),
`--soc0 true` (EKF/UKF start from the true SOC), `--out name` (output file prefix).
Each window prints BIT-EXACT or MISMATCH against the software twin, SOC MAE per estimator, SOH and cycle counts,
and writes `esn_run.csv` and `esn_run.png`.

## 5. Causal streaming and the fused EKF on the board

```
py replay_board.py --vec ..\test_data\sim_causal_b47 --port COM3
py replay_board.py --vec ..\test_data\sim_fused_b47 --port COM3
```
Expected: 1,732 steps each, 0 ESN mismatches (and 0 fused EKF mismatches for `sim_fused_b47`), RESULT PASS.
Cycles per sample on the fast build: ESN 310, fused EKF 477 (first step after a weight load is about 12,700).

## 6. NARMA-10 on the same bitstream (new weights only)

```
py narma_board.py --pack packs/narma10_task_reservoir --port COM3
py narma_board.py --pack packs/narma10_battery_reservoir --port COM3
```
Expected: 2,200 steps, 0 mismatches, NRMSE 0.396 (task reservoir) and 0.556 (battery reservoir).
To replay the other NARMA vector sets: `py replay_board.py --vec ..\test_data\sim_narma10_draw100 --port COM3` (draws 100 to 109).

## 7. Without a board (bit-exact software twin)

```
py esn_host.py twin --pack packs/heldout/pack_B0047 --data packs/heldout/pack_B0047/B0047_cycles.csv --cycle all
py narma_board.py --pack packs/narma10_task_reservoir
py reproduce_paper.py --cells B0005 B0047
py reproduce_paper.py
```
The last command recomputes all 29 held-out cells.

## 8. Train a new model pack (no new bitstream needed)

```
py train_pack.py --mat-dir D:\NASA\Battery --out packs/my_pack
py train_pack.py --mat-dir D:\NASA\Battery --holdout B0047 --out packs/my_B0047
py train_pack.py --csv mycells.csv --ekf-cells CELL_A,CELL_B --out packs/my_cells
```
Then run it with step 4, using `--pack packs/my_pack`.

## 9. Use the IP in your own Vivado design (esn_axi_ip)

Package it once:
```
cd /d D:\esn_ip_platform
vivado -mode batch -source scripts/package_esn_ip.tcl -tclargs D:/esn_ip_platform
```
Then in your project: Settings > IP > Repository > add `D:/esn_ip_platform/ip_repo` > Refresh. Add
"ESN Accelerator (battery SOC/SOH)" (`vesit.ac.in:user:esn_axi_ip:1.0`) to a block design and connect:
`s_axi` to your AXI4-Lite master, `aclk` and `aresetn` to the system clock and reset, `irq` to your interrupt
controller, and optionally `s_axis` / `m_axis` for stream mode. Assign an address in the Address Editor.
`FAST`, `P` and `K` select the core. FAST = 0 is the configuration verified on the board as a packaged IP. The fast
core was verified on the board inside the RV32I system and out of context, but not yet through this packaging
script.

Software: copy `driver/esn_ip.h`, set `ESN_BASE` to the address from the Address Editor, and follow
`driver/esn_ip_example.c` (load Win, W, bias, readouts, input; clear; step; read SOC, SOH and CYCLES).
Registers: `docs/register_map.md`.

## 10. RTL regression (Linux or WSL, Verilator 5)

```
bash scripts/regression.sh
CORE_ARGS="-GFAST=1 -GP=10 -GK=24" bash scripts/regression.sh
bash scripts/narma_draws.sh
CORE_ARGS="-GFAST=1 -GP=10 -GK=24" bash scripts/narma_draws.sh
```
Expected: 10/10 PASS per core and 10/10 PASS for the draws. Reference log: `docs/regression_2026-11-11.txt`.

## 11. Resource sweeps (optional, Vivado)

```
vivado -mode batch -source scripts/sweep_nres.tcl
vivado -mode batch -source scripts/sweep_fast.tcl
```
These build `esn_axi_ip` out of context for N = 50/100/200 and for the fast-core lane counts, and write the
utilization, timing and power reports.

## If something fails

- `no/invalid reply`: wrong COM port, board not programmed with this bitstream, or another program holds the port.
- `MISMATCH`: reload the pack (drop `--skip-load`).
- Window skipped with "no sample with current < -0.25 A": the data uses positive discharge current; flip its sign.
- Vivado "ESN folder not found": run `set ESN_ROOT D:/esn_ip_platform` first.
