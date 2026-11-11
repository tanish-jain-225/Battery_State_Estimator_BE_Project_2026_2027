`timescale 1ns / 1ps
// Stage A test: esn_core + esn_readout, EVERYTHING loaded at run time through
// the load ports from .mem files (no INIT_FILE). 64 steps of NASA B0018 cycle 115.
module tb_esn_core_twice;
reg clk = 1'b0; always #5 clk = ~clk;
reg rst_n = 1'b0, start = 1'b0, clear = 1'b0;
reg [1:0] ld_sel = 0; reg [13:0] ld_addr = 0; reg signed [15:0] ld_data = 0; reg ld_we = 0;
reg rw_we = 0, rw_sel = 0; reg [6:0] rw_addr = 0; reg signed [17:0] rw_data = 0;
wire done, busy, ovf_out, x_valid; wire signed [15:0] x_out; wire [5:0] ts;
wire soc_valid, soh_valid; wire [5:0] soc_step; wire signed [15:0] soc, soh;

esn_core #(.N_IN(4), .N_RES(100), .T_MAX(64)) core (
    .clk(clk), .rst_n(rst_n), .start(start), .clear(clear), .done(done), .busy(busy),
    .timestep_o(ts), .ld_sel(ld_sel), .ld_addr(ld_addr), .ld_data(ld_data), .ld_we(ld_we),
    .x_out(x_out), .x_valid(x_valid), .ovf_out(ovf_out));
esn_readout ro (.clk(clk), .rst_n(rst_n), .clear(clear), .x_in(x_out), .x_valid(x_valid),
    .rw_we(rw_we), .rw_sel(rw_sel), .rw_addr(rw_addr), .rw_data(rw_data),
    .soc(soc), .soc_valid(soc_valid), .soc_step(soc_step), .soh(soh), .soh_valid(soh_valid));

reg [15:0] m_win [0:399]; reg [15:0] m_w [0:9999]; reg [15:0] m_b [0:99]; reg [15:0] m_in [0:255];
reg [17:0] m_rs [0:100]; reg [17:0] m_rh [0:100];
integer fd, i, t, pass;
task ld(input [1:0] sel, input integer a, input [15:0] d);
begin @(negedge clk); ld_sel = sel; ld_addr = a; ld_data = d; ld_we = 1; @(negedge clk); ld_we = 0; end
endtask
always @(posedge clk) begin
    if (soc_valid) $fwrite(fd, "%0d,%04h\n", soc_step, soc);
    if (soh_valid) $fwrite(fd, "SOH,%04h\n", soh);
end
initial begin
    $readmemh("win_bram.mem", m_win); $readmemh("w_bram.mem", m_w); $readmemh("bias_bram.mem", m_b);
    $readmemh("input_c115.mem", m_in); $readmemh("readout_soc.mem", m_rs); $readmemh("readout_soh.mem", m_rh);
    fd = $fopen("rtl_readout.csv", "w"); $fwrite(fd, "step,soc_hex\n");
    repeat (10) @(negedge clk); rst_n = 1'b1; repeat (5) @(negedge clk);
    for (i = 0; i < 400;   i = i + 1) ld(2'd0, i, m_win[i]);
    for (i = 0; i < 10000; i = i + 1) ld(2'd1, i, m_w[i]);
    for (i = 0; i < 256;   i = i + 1) ld(2'd2, i, m_in[i]);
    for (i = 0; i < 100;   i = i + 1) ld(2'd3, i, m_b[i]);
    for (i = 0; i <= 100;  i = i + 1) begin
        @(negedge clk); rw_sel = 0; rw_addr = i; rw_data = m_rs[i]; rw_we = 1;
        @(negedge clk); rw_sel = 1; rw_addr = i; rw_data = m_rh[i];
        @(negedge clk); rw_we = 0;
    end
    for (pass = 0; pass < 2; pass = pass + 1) begin
    if (pass == 1) begin $fclose(fd); fd = $fopen("rtl_readout2.csv", "w"); $fwrite(fd, "step,soc_hex\n"); end
    @(negedge clk); clear = 1'b1; @(negedge clk); clear = 1'b0;
    @(negedge clk); while (busy) @(negedge clk);
    for (t = 0; t < 64; t = t + 1) begin
        @(negedge clk); start = 1'b1; @(negedge clk); start = 1'b0;
        @(posedge done); repeat (20) @(negedge clk);
    end
    repeat (20) @(negedge clk);
    end
    $fclose(fd); $display("tb_esn_core_full done, SOH=%0d", soh); $finish;
end
endmodule
