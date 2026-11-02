## ============================================================
## Design Constraints -- esn_top (Rev 0.12, datapath observable)
## Target board : Digilent Arty A7-100T
## Target device: xc7a100tcsg324-1 (Artix-7 100T, CSG324, speed grade -1)
##
## Top-level ports (esn_top.v Rev 0.12):
##   inputs : clk, rst_n, start
##   outputs: done, x_out[15:0], x_valid, ovf_out
##
## Pin locations follow Digilent's Arty A7 Master XDC. Check them
## against your copy of the master file before programming the board.
## ============================================================

## ------------------------------------------------------------
## Primary clock -- pin E3 (onboard 100 MHz oscillator)
##
## TIMING HISTORY (keep for the paper / lab notes):
##   * Earlier runs (10.000 ns: WNS +6.264 ns; 4.000 ns: closed) used
##     the OLD esn_top, whose only output was `done`. Vivado removed
##     the multiplier, accumulator and tanh table as unobservable
##     logic, so those results describe a control-only design and
##     must NOT be reported.
##   * Patched esn_top (Rev 0.12) at 4.000 ns: WNS = -8.261 ns,
##     134 of 480 endpoints failing -> required period ~12.26 ns,
##     true Fmax ~81.6 MHz (critical path: single-cycle MAC,
##     multiply -> 40-bit add -> round -> saturate).
##   * This file constrains 12.500 ns (80 MHz), which should close.
##
## NOTE: this is a timing-analysis constraint. The Arty oscillator is
## physically fixed at 100 MHz (10 ns), which is FASTER than this
## design can run. To run on the board, generate ~75-80 MHz with a
## Clocking Wizard (MMCM) from the 100 MHz input and clock esn_top
## from the MMCM output (then move create_clock to the MMCM input /
## let Vivado derive the generated clock).
## ------------------------------------------------------------
set_property -dict { PACKAGE_PIN E3   IOSTANDARD LVCMOS33 } [get_ports clk]
create_clock -period 12.500 -name sys_clk -waveform {0.000 6.250} [get_ports clk]
set_clock_uncertainty 0.200 [get_clocks sys_clk]

## ------------------------------------------------------------
## Reset -- BTN0 (pin D9)
## POLARITY: Arty buttons are ACTIVE-HIGH (pressed = 1), but rst_n is
## ACTIVE-LOW. Wired directly, the design sits in reset while the
## button is NOT pressed. Invert BTN0 in a wrapper before rst_n (or
## treat this pin as an active-high run-enable) before using the board.
## ------------------------------------------------------------
set_property -dict { PACKAGE_PIN D9   IOSTANDARD LVCMOS33 } [get_ports rst_n]

## Start -- BTN1 (pin C9), active-high
set_property -dict { PACKAGE_PIN C9   IOSTANDARD LVCMOS33 } [get_ports start]

## ------------------------------------------------------------
## Status outputs -- LEDs
## ------------------------------------------------------------
set_property -dict { PACKAGE_PIN H5   IOSTANDARD LVCMOS33 } [get_ports done]     ;# LD4
set_property -dict { PACKAGE_PIN J5   IOSTANDARD LVCMOS33 } [get_ports ovf_out]  ;# LD5

## ------------------------------------------------------------
## Reservoir state output x_out[15:0] -- Pmod JA (bits 7:0) and JB (bits 15:8)
## x_valid -- Pmod JC pin 1
## These pins make the datapath observable (no synthesis trimming) and
## let a logic analyser capture each x_i(t+1) as it is written back.
## ------------------------------------------------------------
set_property -dict { PACKAGE_PIN G13  IOSTANDARD LVCMOS33 } [get_ports {x_out[0]}]   ;# JA1
set_property -dict { PACKAGE_PIN B11  IOSTANDARD LVCMOS33 } [get_ports {x_out[1]}]   ;# JA2
set_property -dict { PACKAGE_PIN A11  IOSTANDARD LVCMOS33 } [get_ports {x_out[2]}]   ;# JA3
set_property -dict { PACKAGE_PIN D12  IOSTANDARD LVCMOS33 } [get_ports {x_out[3]}]   ;# JA4
set_property -dict { PACKAGE_PIN D13  IOSTANDARD LVCMOS33 } [get_ports {x_out[4]}]   ;# JA7
set_property -dict { PACKAGE_PIN B18  IOSTANDARD LVCMOS33 } [get_ports {x_out[5]}]   ;# JA8
set_property -dict { PACKAGE_PIN A18  IOSTANDARD LVCMOS33 } [get_ports {x_out[6]}]   ;# JA9
set_property -dict { PACKAGE_PIN K16  IOSTANDARD LVCMOS33 } [get_ports {x_out[7]}]   ;# JA10
set_property -dict { PACKAGE_PIN E15  IOSTANDARD LVCMOS33 } [get_ports {x_out[8]}]   ;# JB1
set_property -dict { PACKAGE_PIN E16  IOSTANDARD LVCMOS33 } [get_ports {x_out[9]}]   ;# JB2
set_property -dict { PACKAGE_PIN D15  IOSTANDARD LVCMOS33 } [get_ports {x_out[10]}]  ;# JB3
set_property -dict { PACKAGE_PIN C15  IOSTANDARD LVCMOS33 } [get_ports {x_out[11]}]  ;# JB4
set_property -dict { PACKAGE_PIN J17  IOSTANDARD LVCMOS33 } [get_ports {x_out[12]}]  ;# JB7
set_property -dict { PACKAGE_PIN J18  IOSTANDARD LVCMOS33 } [get_ports {x_out[13]}]  ;# JB8
set_property -dict { PACKAGE_PIN K15  IOSTANDARD LVCMOS33 } [get_ports {x_out[14]}]  ;# JB9
set_property -dict { PACKAGE_PIN J15  IOSTANDARD LVCMOS33 } [get_ports {x_out[15]}]  ;# JB10
set_property -dict { PACKAGE_PIN U12  IOSTANDARD LVCMOS33 } [get_ports x_valid]      ;# JC1

## ------------------------------------------------------------
## I/O timing: buttons, LEDs and Pmod pins are slow, asynchronous
## board-level signals, so exclude them from internal timing analysis.
## The reported WNS/Fmax then reflects the core logic only.
## (For a real high-speed interface, replace these with
##  set_input_delay / set_output_delay.)
## ------------------------------------------------------------
set_false_path -from [get_ports {rst_n start}]
set_false_path -to   [get_ports {done ovf_out x_valid x_out[*]}]

## ------------------------------------------------------------
## Configuration bank voltage (from the Arty A7 master XDC)
## ------------------------------------------------------------
set_property CFGBVS VCCO        [current_design]
set_property CONFIG_VOLTAGE 3.3 [current_design]
