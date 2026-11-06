# ESN Accelerator IP Block & Tri-Observer FPGA Platform (Arty A7-100T)

[← Back to Main Repository](../../README.md) · [← Hardware Overview](../hardware.md) · [← Review 2 Progress](../../docs/Review_2/Review_2_Progress.md) · [Register Map](register_map.md) · [UART Protocol](uart_protocol.md) · [Next: Capstone Thesis →](../../docs/Thesis/README.md)

---

## 📌 Development Flow & Silicon Role

This package represents **Phase 3 (Silicon IP & Acceleration)** of the project development flow. It translates the verified 100-neuron ESN Python model and C99 firmware into a commercial-grade, plug-and-play hardware accelerator packaged to the **IEEE 1685 IP-XACT** standard.

Two deliverables built on the verified Q6.10 ESN datapath (100 neurons, 4 inputs, 64-step window).
The verified MAC / tanh / neuron / controller RTL is **unchanged** (`rtl/esn_neuron.v`, `mac_accum_q6_10.v`, `mult_q6_10.v`, `tanh_lut.v`, `reservoir_controller.v`, `address_generator.v`).

| | What | Top module |
|---|---|---|
| 1 | **Reusable IP** – ESN reservoir + SOC/SOH readout, AXI4-Lite control + AXI4-Stream data, IP-XACT packaging | `esn_axi_ip` |
| 2 | **Platform** – send new battery data from a laptop over USB-UART; ESN, EKF and UKF run on the FPGA at the same time on every sample | `esn_platform_top` (board) / `esn_platform` (core) |

## 1. The IP (`esn_axi_ip`)
* Parameters: `N_IN` (inputs), `N_RES` (neurons), `T_MAX` (window length, power of 2), `READ_LAT` (RAM read latency 1 or 2).
* **All weights are loaded at run time** (Win, W, bias, readout SOC/SOH weights) through the AXI4-Lite memory window → the same bitstream serves any trained ESN of that size / any battery.
* Control/status/IRQ registers: [`register_map.md`](register_map.md). C driver: [`esn_ip.h`](esn_ip.h), [`esn_ip_example.c`](esn_ip_example.c).
* Stream mode: one `s_axis` beat = one input vector u(t); one `m_axis` beat per step = SOC (Q2.14), step index, SOH (valid on TLAST).
* Package for the Vivado IP catalog: IEEE 1685 IP-XACT descriptor provided in [`component.xml`](component.xml) -> add this directory to Vivado *IP Repository Paths*.
* Verified (Verilator, bit-exact vs. the golden readout): register mode and stream mode, 64/64 SOC, SOH `0x31ad`; also N_IN/N_RES/T = 2/2/3, 2/2/64, 3/16/8, 5/33/10, 7/50/16, 16/24/12, 2/128/20, 4/100/64 against an independent integer model; repeated windows after `CLEAR`; RAM latency 1 and 2.

## 2. The platform (`esn_platform_top`)
```
laptop (esn_host.py) --USB-UART 115200 8N1--> [frame parser] -> ESN (esn_core + readout)
                                                           -> EKF (ekf_core)      all three start on the same
                                                           -> UKF (ukf_core)      STEP frame and run in parallel
                     <-- one reply per STEP: SOC(ESN) SOC(EKF) SOC(UKF) SOH(ESN) + measured cycle counts
```
* Everything that depends on the battery is loaded over UART: ESN weights, readout weights, EKF/UKF OCV + slope tables (1024 entries each), EKF/UKF constants. **Same bitstream, any battery** (as long as N_IN/N_RES/T_MAX match).
* Protocol: [`uart_protocol.md`](uart_protocol.md). 80 MHz clock (MMCM from 100 MHz), 115200 baud.
* LEDs: LD4 busy, LD5 good frame, LD6 ESN MAC overflow seen, LD7 MMCM locked.

### Run it on the board
1. `vivado -mode batch -source build_platform.tcl` (or Tools → Run Tcl Script). Creates a **fresh** project with no BRAM IP cores. Bitstream `esn_platform_top.bit` is pre-compiled and ready in this folder.
2. Program the bitstream (`esn_platform_top.bit`).
3. `pip install pyserial numpy matplotlib scipy` then  
   `python esn_host.py run --pack pack_B0018 --data B0047_processed.csv --cycle all --port COM3`  
   (first run loads the model pack, ~3–4 s at 115200 baud; later runs add `--skip-load`).
4. The script prints, per discharge cycle, whether the chip is **bit-exact with its software twin**, MAE per estimator if the file has a true `soc` column, the SOH, and the measured clock cycles; it writes `esn_run.csv` and `esn_run.png`.

### Data accepted by `esn_host.py`
CSV with `time, voltage_measured, current_measured, temperature_measured` (+ optional `current_load, cycle, soc, capacity`) or a NASA `.mat` (`--cycle N|all`). Each cycle is resampled to 64 steps (one ESN window). Discharge current negative. EKF/UKF start SOC defaults to 1.0 (`--soc0`), capacity from the file's first `capacity` value (`--cap` to override).

### Without the board (simulation flow)
`python esn_host.py run --pack pack_B0018 --data b18.csv --emit simdir` → writes the exact UART byte stream (`frames.mem`, `flens.mem`).  
Copy those and `tanh.mem` into the simulation working directory, run `tb_esn_platform` (Vivado XSim or `regression.sh` style Verilator), then `... --replay simdir/resp.txt` checks the chip's replies.  
`regression.sh` re-runs all bundled tests with Verilator.

## 3. Verification status (what was actually run)
| Test | Result |
|---|---|
| AXI IP register + stream mode vs golden SOC/SOH | 64/64 bit-exact, SOH 0x31ad |
| Platform, NASA B0018 cycle 115 via UART (ESN+EKF+UKF) | 64/64 steps bit-exact vs Python golden / software twin, SOH 0x31ad |
| Platform, NASA B0018 fold, all 8 cycles × 64 steps (512 steps, repeated CLEAR/INIT) | ESN, EKF, UKF, SOH: 0 mismatches vs the verified golden traces |
| Platform, **unseen** cell B0047 (4 cycles) | chip = software twin, 0 mismatches |
| EKF / UKF cores after adding table-load ports | 512/512 vs golden (unchanged results) |
| Measured cycles per sample (simulation) | ESN 42,905 (536 µs @ 80 MHz) · EKF 226 · UKF 597 |

**Not yet measured / not claimed:** FPGA resource use, Fmax and power of `esn_platform_top` and `esn_axi_ip` (synthesise and read `vivado/reports/`); board run of the platform bitstream; Ethernet (UART only for now).

## 4. Limits you should know
* **The shipped model pack is trained on NASA room-temperature cells (B0005/6/7).** On the unseen cold-temperature cell B0047 the chip reproduces its software twin bit-exactly, but the *ESN* estimates are not accurate there (SOC MAE ≈ 0.73–0.77 in simulation, outside the training distribution), while EKF/UKF stay at ≈ 0.5–1.3 %. For a new chemistry or temperature, retrain ESN + readout and refit the OCV curve in Python, build a new pack (`host/make_pack.py` shows the format), and load it – no new bitstream needed.
* EKF/UKF need an initial SOC from the host (default 1.0 = full); the ESN does not.
* SOH is the mean over one 64-step window, so one window = one discharge cycle (resampled).
* Throughput is limited by the 115200-baud UART (~4 ms per sample incl. frames), not by the 0.54 ms ESN compute.

---

[← Return to Review 2 Progress](../../docs/Review_2/Review_2_Progress.md) · [Proceed to B.E. Final Thesis →](../../docs/Thesis/README.md) · [Academic Publications →](../../docs/Publications/README.md)
