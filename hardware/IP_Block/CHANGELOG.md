# Changelog

## 1.2 (11 Nov 2026)
Hardware (RTL changed; rebuild bitstreams):
* `rtl/esn_core_fast.v`: scalable core, drop-in for `esn_core` (same ports, load map and arithmetic, bit-exact).
  One MAC term per clock, zero recurrent weights skipped through a one-time ELL compression after each weight load,
  P parallel lanes. Generics `FAST`, `P`, `K` on `esn_axi_ip`, `esn_platform` and `esn_platform_top`; default `FAST=0`
  keeps the serial core. Cycle model ceil(N/P)(N_IN+K) + 2L + P + 13 (307 cycles at N=100, P=10, K=24, L=2).
  A row with more than K nonzeros sets STATUS bit 3 (IP) or the overflow flag (platform).
* `rtl/ekf_core.v` Rev 0.5: optional ESN fusion. After the voltage update, a second scalar update uses the ESN SOC of
  the same step as a direct SOC measurement (registers 32 RE, 33 FUSE). FUSE = 0 reproduces Rev 0.4 exactly
  (245 cycles). Fused output: 477 cycles per sample on the 10-lane platform. Rev 0.4 baseline archived in git history (`hardware/FPGA_Verifier/ekf/rtl/ekf_core.v` retains the standalone serial EKF verifier).
* `rtl/esn_platform.v`: connects the ESN SOC to the EKF fusion input; 6-bit EKF configuration address.
* `scripts/build_platform.tcl`: `set ESN_FAST {1 10 24}`, or `-tclargs fast` in batch mode, builds the fast platform in `vivado_fast/`.
* `scripts/package_esn_ip.tcl` now also adds `esn_core_fast.v`, so the packaged IP can be set to the fast core.
* `RUN_COMMANDS.md`: every command to build, program, run and check the IP and the platform.

Verification and host:
* Regression now covers 10 tests per core (AXI IP register/stream, 4 battery replays, 2 NARMA-10 replays, causal
  streaming B0047, fused EKF B0047) and runs on both cores; `scripts/narma_draws.sh` replays ten further NARMA-10
  reservoirs. Log of 11 Nov 2026 in `docs/regression_2026-11-11.txt`.
* `host/golden/ekf_fixed.py` (class `EKFFixed`, with `fuse=`), `host/golden/esn_fast.py`, `host/replay_board.py`
  (replays any `test_data/sim_*` vector set on the board), `host/narma_board.py`.
* New test vectors: `sim_causal_b47`, `sim_fused_b47`, `sim_narma10_task`, `sim_narma10_battery`, `sim_narma10_draw100..109`.

## 1.1 (8 Nov 2026)
Hardware (RTL, testbenches, constraints, Tcl scripts): **unchanged**. Bitstreams built from 1.0 work with 1.1.

Host software and model packs:
* `esn_host.py` now ends every window at the last sample with current below -0.25 A (post-load rest data removed),
  as in the paper. `--no-trim` keeps the old behaviour. Windows with fewer than 16 loaded samples are skipped.
* `esn_host.py twin`: runs the bit-exact software twin without a board.
* EKF/UKF capacity default is now the median of the first three windows' capacities (the paper's choice) instead
  of the first one; `--cap` still overrides.
* Default pack is `packs/general_32cells` (all 32 usable NASA cells, all temperatures, discharge-only windows).
* New `packs/heldout/pack_<cell>` for all 29 evaluation cells, each with its test CSV, and `packs/pack_B0047_24C_only`.
* EKF/UKF tables in every pack are calibrated on the 4 reference cells (the paper's setting).
* New `train_pack.py` (self-contained; rebuilds `general_32cells` exactly) and `reproduce_paper.py`.
* Legacy October room-temperature packs and builders (which retained post-load rest data) are archived in git history (removed from working tree in the v2.4.0 storage deduplication pass).
* README rewritten with measured results; regression log in `docs/`.

## 1.0 (27-28 Oct 2026)
First release: `esn_axi_ip`, `esn_platform`, UART protocol, C driver, Verilator regression, room-temperature packs.
