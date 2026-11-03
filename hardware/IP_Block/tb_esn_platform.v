`timescale 1ns / 1ps
// Replays a UART frame stream (frames.mem bytes, flens.mem lengths) into esn_platform and logs every response byte.
module tb_esn_platform;
parameter CPB = 8;
reg clk = 0; always #5 clk = ~clk;
reg rst_n = 0; reg rx = 1; wire tx, busy, fok, ovf;
esn_platform #(.CLKS_PER_BIT(CPB), .TIMEOUT(2000000)) dut (.clk(clk), .rst_n(rst_n), .uart_rx_i(rx), .uart_tx_o(tx),
    .busy_o(busy), .frame_ok_o(fok), .ovf_seen_o(ovf));

reg [7:0]  fm [0:262143];
reg [31:0] fl [0:65535];
integer nfr, f, ofs, b, k, fd, resp_cnt;

// ---- response monitor ----
reg [7:0] rb; integer rk, rs, rlen, rgot;
reg [7:0] rcmd; reg [15:0] rl;
initial begin rs = 0; resp_cnt = 0; end
always @(negedge tx) begin : mon
    integer j; reg [7:0] d;
    #(CPB*10/2);
    d = 0;
    for (j = 0; j < 8; j = j + 1) begin #(CPB*10); d[j] = tx; end
    #(CPB*10);
    $fdisplay(fd, "%02x", d);
    case (rs)
    0: if (d == 8'hA5) rs = 1;
    1: begin rcmd = d; rs = 2; end
    2: begin rl[7:0] = d; rs = 3; end
    3: begin rl[15:8] = d; rgot = 0; rs = (rl == 0) ? 5 : 4; end
    4: begin rgot = rgot + 1; if (rgot == rl) rs = 5; end
    5: begin rs = 0; resp_cnt = resp_cnt + 1; end
    endcase
end

task sendb(input [7:0] d);
integer j;
begin
    rx = 0; repeat (CPB) @(posedge clk);
    for (j = 0; j < 8; j = j + 1) begin rx = d[j]; repeat (CPB) @(posedge clk); end
    rx = 1; repeat (CPB) @(posedge clk);
end
endtask

initial begin
    $readmemh("frames.mem", fm); $readmemh("flens.mem", fl);
    fd = $fopen("resp.txt", "w");
    nfr = fl[0]; ofs = 0;
    repeat (20) @(posedge clk); rst_n = 1; repeat (20) @(posedge clk);
    for (f = 0; f < nfr; f = f + 1) begin
        for (b = 0; b < fl[f+1]; b = b + 1) sendb(fm[ofs + b]);
        ofs = ofs + fl[f+1];
        k = 0;
        while (resp_cnt < f + 1) begin @(posedge clk); k = k + 1; if (k > 4000000) begin $display("TIMEOUT waiting reply to frame %0d", f); $fclose(fd); $finish; end end
    end
    repeat (200) @(posedge clk);
    $fclose(fd); $display("PLATFORM TB done: %0d frames", nfr); $finish;
end
endmodule
