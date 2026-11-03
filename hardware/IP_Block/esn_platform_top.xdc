## esn_platform_top.xdc -- Arty A7-100T (xc7a100tcsg324-1). Use ONLY this XDC for the platform build.
set_property -dict { PACKAGE_PIN E3  IOSTANDARD LVCMOS33 } [get_ports clk100]
create_clock -period 10.000 -name clk100 -waveform {0.000 5.000} [get_ports clk100]
set_clock_uncertainty 0.200 [get_clocks -of_objects [get_pins u_mmcm/CLKOUT0]]

set_property -dict { PACKAGE_PIN C2  IOSTANDARD LVCMOS33 } [get_ports ck_rst_n]   ;# red RESET button
set_property -dict { PACKAGE_PIN A9  IOSTANDARD LVCMOS33 } [get_ports uart_rx_i]  ;# FT2232 TXD -> FPGA RX
set_property -dict { PACKAGE_PIN D10 IOSTANDARD LVCMOS33 } [get_ports uart_tx_o]  ;# FPGA TX -> FT2232 RXD
set_property -dict { PACKAGE_PIN H5  IOSTANDARD LVCMOS33 } [get_ports {led[0]}]   ;# LD4 running
set_property -dict { PACKAGE_PIN J5  IOSTANDARD LVCMOS33 } [get_ports {led[1]}]   ;# LD5 good frame
set_property -dict { PACKAGE_PIN T9  IOSTANDARD LVCMOS33 } [get_ports {led[2]}]   ;# LD6 overflow seen
set_property -dict { PACKAGE_PIN T10 IOSTANDARD LVCMOS33 } [get_ports {led[3]}]   ;# LD7 MMCM locked

set_false_path -from [get_ports {ck_rst_n uart_rx_i}]
set_false_path -to   [get_ports {uart_tx_o led[*]}]

set_property CFGBVS VCCO        [current_design]
set_property CONFIG_VOLTAGE 3.3 [current_design]
