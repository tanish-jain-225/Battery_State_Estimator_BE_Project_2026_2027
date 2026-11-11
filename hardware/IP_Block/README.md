[← Back to Main Repository](../../README.md) · [← Hardware Overview](../hardware.md) · [← Review 2 Progress](../../docs/Review_2/Review_2_Progress.md) · [Run Commands](RUN_COMMANDS.md) · [Register Map](docs/register_map.md) · [UART Protocol](docs/uart_protocol.md) · [Next: Capstone Thesis →](../../docs/Thesis/README.md)

# ESN battery SOC/SOH accelerator for FPGA (Arty A7-100T)

Version 1.2, 11 Nov 2026 (final release). See [`CHANGELOG.md`](CHANGELOG.md) for what changed since 1.1: the scalable fast core ([`rtl/esn_core_fast.v`](rtl/esn_core_fast.v)), the
ESN-fused EKF ([`rtl/ekf_core.v`](rtl/ekf_core.v) Rev 0.5), causal streaming and NARMA-10 test vectors, and a regression that runs on both cores.

> **Repository Artifacts Note:** For immediate plug-and-play Vivado inspection and flashing without recompilation, this folder also retains the pre-built **v1.0 serial (`FAST=0`, `ekf_core` Rev 0.4)** IEEE 1685 IP-XACT descriptor ([`component.xml`](component.xml)), pre-compiled Arty A7-100T bitstream ([`esn_platform_top.bit`](esn_platform_top.bit)), and routed Vivado 2023.1 baseline reports in [`reports_v10/`](reports_v10/). To build the **v1.2 fast-core (`FAST=1, P=10, K=24`) + Rev 0.5 fused-EKF** bitstream or repackage IP-XACT with `esn_core_fast.v`, run `scripts/build_platform.tcl -tclargs fast` or `scripts/package_esn_ip.tcl` per [`RUN_COMMANDS.md`](RUN_COMMANDS.md).

A fixed-point echo state network (ESN) for lithium-ion battery state of charge (SOC) and an exploratory
state-of-health (SOH) readout, in Verilog, verified bit-exact against a Python model in simulation and on the board.
The package has two hardware deliverables and the host software to use them:

| | What | Top module | Use it when |
|---|---|---|---|
| 1 | **Reusable IP**: ESN reservoir + SOC/SOH readouts, AXI4-Lite control, AXI4-Stream data, IP-XACT packaging | `esn_axi_ip` | you want the ESN inside your own Vivado block design (MicroBlaze, Zynq, your own master) |
| 2 | **Platform**: laptop sends battery data over USB-UART; ESN, EKF and UKF run on the FPGA side by side on every sample | `esn_platform_top` (board), `esn_platform` (core) | you want to run or demonstrate estimation on the Arty board |

Fixed design parameters of the shipped builds: 4 inputs (voltage, current, temperature, load current),
100 neurons, 64-step window, Q6.10 datapath, Q4.14 readouts, 80 MHz.

Two reservoir cores with identical arithmetic and identical outputs, selected by a synthesis generic:

| Core | Generics | Cycles per update (N=100) | When to use |
|---|---|---|---|
| serial `esn_core` | `FAST=0` (default) | 42,902 (536 µs at 80 MHz) | smallest area (IP: 1,868 LUTs, 4 DSP) |
| scalable `esn_core_fast` | `FAST=1 P=<lanes> K=<max nonzeros per row>` | 307 at P=10, K=24 (3.84 µs) | latency; sparse reservoirs (IP: 4,877 LUTs, 22 DSP at P=10) |

The platform EKF (Rev 0.5) can also take the ESN SOC as a second measurement (register FUSE = 1).
Everything that depends on the battery (weights, input scaling, EKF/UKF tables) is loaded at run time, so the
same bitstream serves any trained model of that size.

Every command to build, program and run is in `RUN_COMMANDS.md`.

## Folder map

```
rtl/        Verilog. Verified core (unchanged since the 200/200 and 6400/6400 checks): esn_neuron, mac_accum_q6_10,
            mult_q6_10, tanh_lut, reservoir_controller, address_generator. Wrappers: esn_core, esn_core_fast
            (scalable core), esn_ram, esn_readout, esn_axi_ip (IP), esn_platform(_top), ekf_core (Rev 0.5, fusion),
            ukf_core, uart_rx/tx
backup_rev04/ ekf_core and platform before ESN fusion (reference only)
mem/        tanh.mem (5121-entry tanh table, needed by synthesis and simulation)
xdc/        Arty A7-100T constraints for the platform
scripts/    build_platform.tcl (fresh Vivado project + bitstream; `set ESN_FAST {1 10 24}` for the fast core),
            package_esn_ip.tcl (IP catalog), regression.sh (Verilator regression, either core),
            narma_draws.sh (ten NARMA-10 reservoir draws), sweep_nres.tcl / sweep_fast.tcl (resource sweeps)
tb/         testbenches (AXI IP, platform UART replay, core)
verify/     golden vectors for the AXI IP test (B0018 cycle 115)
test_data/  UART replay vectors: battery windows, causal streaming (sim_causal_b47), fused EKF (sim_fused_b47),
            NARMA-10 (task, battery reservoir, draws 100-109)
driver/     C driver for the AXI IP (esn_ip.h) + example
docs/       register_map.md (IP), uart_protocol.md (platform)
host/       esn_host.py      run data on the board, or on the bit-exact software twin without a board
            train_pack.py    train a new model pack from your own data (no new bitstream needed)
            reproduce_paper.py  recompute the 29-cell results from the shipped packs
            replay_board.py  send any test_data vector set to the board and compare every step with the twin
            narma_board.py   NARMA-10 on the board with new weights only
            packs/           model packs (below)
            golden/          bit-exact Python models: EKF (EKFFixed, with fusion), UKF, fast core, EKF calibration
            legacy_oct2026/  superseded October packs and builders (do not use)
```

## Quick start without a board (5 minutes)

```
pip install numpy scipy scikit-learn pyserial matplotlib
cd host
python esn_host.py twin --data packs/heldout/pack_B0047/B0047_cycles.csv --pack packs/heldout/pack_B0047 --cycle all
python reproduce_paper.py --cells B0005 B0047
```
`twin` runs the bit-exact software model of the chip (same integers the FPGA produces) and prints SOC MAE for
ESN, EKF and UKF when the data has a `soc` column. `reproduce_paper.py` with no arguments recomputes all 29 cells.

## Quick start on the Arty A7-100T

1. Build: `vivado -mode batch -source scripts/build_platform.tcl` (Vivado 2023.1; creates `vivado/esn_platform.xpr`
   with no BRAM IP cores, reports in `vivado/reports/`). Or in the GUI: add `rtl/*.v`, `mem/tanh.mem`,
   `xdc/esn_platform_top.xdc`, top `esn_platform_top`.
2. Program the bitstream (Hardware Manager). LD7 on = clock locked.
3. Find the board's COM port (Device Manager, "USB Serial Port"), then from `host/`:
   ```
   python esn_host.py ping --port COM5
   python esn_host.py run --pack packs/general_32cells --data packs/heldout/pack_B0047/B0047_cycles.csv --cycle all --port COM5
   ```
   The first run loads the model pack (about 3.5 s at 115200 baud); add `--skip-load` on later runs with the same pack.
   For each window it prints whether the chip is **bit-exact with the software twin**, the SOC MAE per estimator,
   the SOH, and the measured clock cycles, and writes `esn_run.csv` and `esn_run.png`.

LEDs: LD4 busy, LD5 good frame, LD6 ESN MAC overflow seen, LD7 clock locked.

## Model packs (`host/packs/`)

| Pack | Trained on | Use |
|---|---|---|
| `general_32cells` (default) | all 32 NASA PCoE cells that have valid discharge windows, 4 to 44 °C, 1 to 4 A | general use and demos |
| `heldout/pack_<cell>` (29 packs) | every cell except `<cell>`; each folder also holds `<cell>_cycles.csv` | reproduce the paper's cross-cell results, test on data the model never saw |
| `pack_B0047_24C_only` | the four 24 °C reference cells only | shows why training coverage matters (cold cell B0047: SOC MAE about 0.20 vs 0.04 with all conditions) |

All packs share the same reservoir (Win, W, bias, tanh) and differ only in input scaling, readouts and EKF/UKF tables.
EKF/UKF tables are calibrated on the reference cells B0005, B0006, B0007, B0018 (excluding a held-out one).

### Train your own pack
```
python train_pack.py --mat-dir path/to/NASA/Battery --out packs/my_pack                 # NASA .mat files
python train_pack.py --mat-dir path/to/NASA/Battery --holdout B0047 --out packs/my_B0047 # keep one cell out
python train_pack.py --csv mycells.csv --ekf-cells CELL_A,CELL_B --out packs/my_cells     # your own data
```
Own-data CSV: one row per sample with `cell, cycle, time, voltage, current, temperature, [current_load], capacity`
(discharge current negative, capacity in Ah for that discharge). `train_pack.py --mat-dir` on the NASA data rebuilds
`general_32cells` file for file.

## Data rules (the host tools and packs all follow them)

* Discharge current is negative (NASA convention).
* Each window is one discharge and ends at its last sample with current below -0.25 A, so data logged after the load
  is switched off (post-load rest) is not fed to the estimators. Windows with fewer than 16 loaded samples are skipped.
  `--no-trim` restores the old behaviour, only for comparing with October runs.
* Each window is resampled to 64 steps; the ESN state is cleared at the start of each window.
* SOC truth (if given) is Coulomb counting against that discharge's capacity, so it starts at 1 (full charge assumed).
* EKF/UKF need an initial SOC (`--soc0`, default 1.0) and a capacity (default: median of the first three windows'
  `capacity` values; `--cap 2.0` gives the rated-capacity EKF). The ESN needs neither.

## The IP (`esn_axi_ip`)

* Parameters: `N_IN`, `N_RES`, `T_MAX` (power of 2), `READ_LAT` (RAM read latency 1 or 2).
* All weights (Win, W, bias, SOC/SOH readouts) are written through the AXI4-Lite memory window at run time.
* Registers, IRQ and the memory window: `docs/register_map.md`. C driver: `driver/esn_ip.h`, example `driver/esn_ip_example.c`.
* Stream mode: one `s_axis` beat = one input vector u(t); one `m_axis` beat per step = SOC (Q2.14), step index, SOH (valid on TLAST).
* Package: `vivado -mode batch -source scripts/package_esn_ip.tcl -tclargs <this folder>`, then add `ip_repo/` under
  Settings > IP > Repository. Appears as `vesit.ac.in:user:esn_axi_ip:1.0`, "ESN Accelerator (battery SOC/SOH)".

## Verification and measured results

| Check | Result | Where |
|---|---|---|
| RTL regression (Verilator 5.028), serial core and fast core (P=10, K=24): AXI IP register + stream mode, 4 battery replays, NARMA-10 task and battery reservoir, causal B0047 (1,732 steps), fused EKF B0047 | 10/10 PASS on each core, 0 mismatches (11 Nov 2026, `docs/regression_2026-11-11.txt`) | `scripts/regression.sh` |
| Ten further NARMA-10 reservoirs | 10/10 PASS, 2,200 steps each, 0 mismatches (serial core 11 Nov; both cores 10 Nov) | `scripts/narma_draws.sh` |
| Fast platform on the board (P=10, K=24): NARMA-10 2,200 steps, B0047 69 windows; fused EKF B0047 1,732 steps | all bit-exact with the twin; cycles ESN 310, EKF 245, fused EKF 477 | Nov 10, `host/replay_board.py` |
| RV32I soft-processor system with the fast IP and the unchanged C driver | PASS 64/64 + SOH, CYCLES 307 | Nov 10 |
| Software twin vs paper, 29 held-out packs | identical: ESN 0.0667, EKF 0.0631 / 0.0740, per-cell SD 0.0204 | `host/reproduce_paper.py` |
| AXI IP on the board (JTAG-AXI master, AXI-Stream FIFO, RV32I soft core with the C driver) | SOC 64/64 and SOH 0x31AD bit-exact in all three systems | Oct 28-30 |
| Platform on the board, cells B0018 (8 windows) and B0047 | ESN, EKF, UKF and SOH bit-exact with the software twin in every window | Oct 28, Nov 5 |
| Platform, serial core, routed, 80 MHz | WNS +1.317 ns; 13,861 LUTs, 9,265 FFs, 18.5 BRAM, 12 DSP; 0.368 W (Vivado estimate) | |
| Platform, fast core P=10 + fused EKF, routed, 80 MHz | WNS +0.251 ns; 17,290 LUTs, 12,098 FFs, 38.5 BRAM, 30 DSP; 0.447 W (Vivado estimate) | |
| IP, fast core P=10, K=24, out of context | 4,877 LUTs, 7,262 FFs, 34.5 BRAM, 22 DSP; 0.156 W, 0.60 µJ per update (estimate) | |
| ESN reservoir core alone | 318 LUTs, 311 FFs, 11.5 BRAM, 2 DSP; WNS +0.023 ns | |
| IP, out of context | 1,868 LUTs, 4,466 FFs, 14.5 BRAM, 4 DSP; 0.131 W (estimate) | |
| Cycles per input sample (measured on chip) | ESN 42,905 serial / 310 fast (first step after a weight load 12,714, includes compression), EKF 245, fused EKF 477, UKF 662 | |
| Accuracy, 29 held-out cells | SOC MAE: ESN 0.067, EKF measured capacity 0.063, EKF rated capacity 0.074 | `reproduce_paper.py` |

## Limits to know before using it

* The packs and `esn_host.py run` are window-based (a discharge resampled to 64 steps). Causal, sample-by-sample
  streaming is verified in RTL and on the board with recorded data (`sim_causal_b47`, `sim_fused_b47`), state cleared
  at each sequence start; live sensors and continuous charge/rest/partial cycles are not demonstrated.
* The fast core needs K at least the largest number of nonzeros in any row of W; otherwise STATUS bit 3 is set.
* The SOH readout is exploratory (R² 0.217 across the 29-cell cohort).
* The model is only as good as its training coverage. For a new chemistry, temperature range or load profile,
  train a pack on representative data with `train_pack.py`.
* Power numbers are Vivado vectorless estimates, not board measurements.
* Throughput is limited by the 115200-baud UART (about 4 ms per sample including frames), not by the compute
  (0.54 ms serial, 3.9 µs fast).

## Troubleshooting

* `no/invalid reply`: wrong COM port, board not programmed with this bitstream, or another program holds the port.
  `ping` must answer `N_IN 4, N_RES 100, T 64`.
* `python` not found on Windows: use `py` instead of `python`.
* `MISMATCH` against the twin: reload the pack (drop `--skip-load`); a WRITE with a bad checksum can leave a partial write.
* Window skipped with "no sample with current < -0.25 A": the file probably uses positive discharge current; flip its sign.

---

[← Return to Review 2 Progress](../../docs/Review_2/Review_2_Progress.md) · [Proceed to B.E. Final Thesis →](../../docs/Thesis/README.md) · [Academic Publications →](../../docs/Publications/README.md)
