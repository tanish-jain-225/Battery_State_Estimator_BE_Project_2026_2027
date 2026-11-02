## ============================================================
## Design Constraints -- ekf_core (Rev 0.2), out-of-context synthesis
## Target device: xc7a100tcsg324-1 (Artix-7 100T, speed grade -1)
##
## Use ONLY this file for the EKF run. Disable esn_top.xdc
## (right-click -> Disable File) or use a separate project.
## Synthesis option required: -mode out_of_context
##
## Why no PACKAGE_PIN lines: ekf_core has 76 ports (32-bit cfg_data,
## 32-bit soc_out, ...), more than the Arty's free user pins. As a
## submodule it is meant to sit next to the ESN, driven by on-chip
## logic, so it is characterised out of context, like an IP core.
## ============================================================

## ------------------------------------------------------------
## Clock: 12.5 ns (80 MHz) -- same target as esn_top, for a fair
## ESN-vs-EKF comparison.
## ------------------------------------------------------------
create_clock -period 12.500 -name clk -waveform {0.000 6.250} [get_ports clk]
set_clock_uncertainty 0.200 [get_clocks clk]

## ------------------------------------------------------------
## I/O timing: same treatment as esn_top.xdc -- the ports are slow
## configuration / status signals, so they are excluded from timing
## analysis and the reported WNS / Fmax reflects the core logic only.
## (Board pads add ~4 ns of IBUF/OBUF + routing that a submodule
##  sitting next to the ESN would never see.)
## ------------------------------------------------------------
set_false_path -from [get_ports {rst_n cfg_we cfg_addr[*] cfg_data[*] init start}]
set_false_path -to   [get_ports {done busy soc_out[*]}]
