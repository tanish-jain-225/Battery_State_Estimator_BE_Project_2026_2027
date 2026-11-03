`timescale 1ns / 1ps
// uart_rx.v -- 8N1 UART receiver (mid-bit sampling). CLKS_PER_BIT = f_clk / baud.
module uart_rx #(parameter CLKS_PER_BIT = 694) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       rx,
    output reg        valid,      // 1-cycle pulse per received byte
    output reg  [7:0] data
);
localparam S_IDLE = 2'd0, S_START = 2'd1, S_DATA = 2'd2, S_STOP = 2'd3;
reg [1:0]  rxs;
reg [1:0]  st;
reg [15:0] cnt;
reg [2:0]  bi;
reg [7:0]  sh;
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        rxs <= 2'b11; st <= S_IDLE; cnt <= 16'd0; bi <= 3'd0; sh <= 8'd0; valid <= 1'b0; data <= 8'd0;
    end else begin
        rxs   <= {rxs[0], rx};
        valid <= 1'b0;
        case (st)
        S_IDLE:  if (!rxs[1]) begin cnt <= 16'd0; st <= S_START; end
        S_START: if (cnt == CLKS_PER_BIT/2 - 1) begin
                     cnt <= 16'd0;
                     if (!rxs[1]) begin st <= S_DATA; bi <= 3'd0; end else st <= S_IDLE;
                 end else cnt <= cnt + 1'b1;
        S_DATA:  if (cnt == CLKS_PER_BIT - 1) begin
                     cnt <= 16'd0; sh <= {rxs[1], sh[7:1]};
                     if (bi == 3'd7) st <= S_STOP; else bi <= bi + 1'b1;
                 end else cnt <= cnt + 1'b1;
        S_STOP:  if (cnt == CLKS_PER_BIT - 1) begin
                     cnt <= 16'd0; st <= S_IDLE;
                     if (rxs[1]) begin valid <= 1'b1; data <= sh; end
                 end else cnt <= cnt + 1'b1;
        endcase
    end
end
endmodule
