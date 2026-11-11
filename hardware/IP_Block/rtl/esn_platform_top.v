`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////
// esn_platform_top.v -- Arty A7-100T wrapper for esn_platform (ESN + EKF + UKF over USB-UART)
//   100 MHz -> MMCM -> 80 MHz, 115200 8N1 on the USB-UART (FT2232), reset = red RESET button
//   LD4 running, LD5 good frame received (stretched), LD6 ESN MAC overflow seen, LD7 MMCM locked
//////////////////////////////////////////////////////////////////////////////
module esn_platform_top #(
    parameter CLKS_PER_BIT = 694,
    parameter FAST = 0, parameter P = 1, parameter K = 100
)(
    input  wire       clk100,
    input  wire       ck_rst_n,
    input  wire       uart_rx_i,
    output wire       uart_tx_o,
    output wire [3:0] led
);
wire clkfb, clkfb_buf, clk80_unbuf, clk80, locked;
MMCME2_BASE #(.CLKIN1_PERIOD(10.0), .DIVCLK_DIVIDE(1), .CLKFBOUT_MULT_F(10.0), .CLKOUT0_DIVIDE_F(12.5)) u_mmcm (
    .CLKIN1(clk100), .CLKFBIN(clkfb_buf), .CLKFBOUT(clkfb),
    .CLKOUT0(clk80_unbuf), .CLKOUT0B(), .CLKOUT1(), .CLKOUT1B(), .CLKOUT2(), .CLKOUT2B(),
    .CLKOUT3(), .CLKOUT3B(), .CLKOUT4(), .CLKOUT5(), .CLKOUT6(), .CLKFBOUTB(),
    .LOCKED(locked), .PWRDWN(1'b0), .RST(~ck_rst_n));
BUFG u_bufg_fb  (.I(clkfb),       .O(clkfb_buf));
BUFG u_bufg_clk (.I(clk80_unbuf), .O(clk80));

reg [2:0] rst_sync;
always @(posedge clk80 or negedge locked)
    if (!locked) rst_sync <= 3'b000; else rst_sync <= {rst_sync[1:0], ck_rst_n};
wire rst_n = rst_sync[2];

reg [1:0] rx_s;                                    // metastability filter for the asynchronous RX pin
always @(posedge clk80) rx_s <= {rx_s[0], uart_rx_i};

wire busy, fok, ovf;
esn_platform #(.CLKS_PER_BIT(CLKS_PER_BIT), .TIMEOUT(4000000), .FAST(FAST), .P(P), .K(K)) u_plat (
    .clk(clk80), .rst_n(rst_n), .uart_rx_i(rx_s[1]), .uart_tx_o(uart_tx_o),
    .busy_o(busy), .frame_ok_o(fok), .ovf_seen_o(ovf));

reg [21:0] stretch;
always @(posedge clk80 or negedge rst_n)
    if (!rst_n) stretch <= 22'd0; else if (fok) stretch <= {22{1'b1}}; else if (stretch != 0) stretch <= stretch - 1'b1;
assign led = {locked, ovf, |stretch, busy};
endmodule
