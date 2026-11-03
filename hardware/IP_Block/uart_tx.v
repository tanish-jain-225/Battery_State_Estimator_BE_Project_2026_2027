`timescale 1ns / 1ps
// uart_tx.v -- 8N1 UART transmitter. CLKS_PER_BIT = f_clk / baud (80 MHz / 115200 = 694)
module uart_tx #(parameter CLKS_PER_BIT = 694) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       send,      // 1-cycle pulse, accepted when !busy
    input  wire [7:0] data,
    output reg        tx,
    output wire       busy
);
reg [15:0] cnt;
reg [3:0]  bit_idx;            // 0 = start, 1..8 = data, 9 = stop
reg [9:0]  shreg;
reg        active;
assign busy = active;
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        tx <= 1'b1; cnt <= 0; bit_idx <= 0; shreg <= 10'h3FF; active <= 1'b0;
    end else if (!active) begin
        tx <= 1'b1;
        if (send) begin
            shreg <= {1'b1, data, 1'b0}; active <= 1'b1; cnt <= 0; bit_idx <= 0;
            tx <= 1'b0;
        end
    end else begin
        if (cnt == CLKS_PER_BIT - 1) begin
            cnt <= 0;
            if (bit_idx == 4'd9) begin
                active <= 1'b0; tx <= 1'b1;
            end else begin
                bit_idx <= bit_idx + 1'b1;
                tx <= shreg[bit_idx + 1];
            end
        end else
            cnt <= cnt + 1'b1;
    end
end
endmodule
