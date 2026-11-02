`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////
// tb_ukf_core.v -- drives ukf_core with real NASA cycles (stim from gen_ukf.py)
// and logs the trace registers after every step to rtl_ukf_trace.csv.
// Needs: ukf_stim.mem, ukf_ocv.mem, ukf_slope.mem (simulation sources) and
//        (no include files needed -- trace format is inlined).
//////////////////////////////////////////////////////////////////////////////
module tb_ukf_core;

reg clk = 1'b0;
always #5 clk = ~clk;                       // 100 MHz simulation clock

reg rst_n = 1'b0, cfg_we = 1'b0, start = 1'b0;
reg  [5:0]         cfg_addr = 6'd0;
reg  signed [31:0] cfg_data = 32'sd0;
wire done, busy;
wire signed [31:0] soc_out;

ukf_core #(.OCV_FILE("ukf_ocv.mem"), .SLOPE_FILE("ukf_slope.mem")) dut (
    .clk(clk), .rst_n(rst_n), .cfg_we(cfg_we), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
    .start(start), .done(done), .soc_out(soc_out), .busy(busy));

reg [31:0] stim [0:65535];
integer fd, n_cyc, n_steps, n_wr, c, t, w, ptr, step_no, cyc_start, cyc_total;

task wr(input [5:0] addr, input [31:0] data);
begin
    @(negedge clk); cfg_we = 1'b1; cfg_addr = addr; cfg_data = data;
    @(negedge clk); cfg_we = 1'b0;
end
endtask

initial begin
    $readmemh("ukf_stim.mem", stim);
    fd = $fopen("rtl_ukf_trace.csv", "w");
    $fwrite(fd, "step,t,i,vm,x0p,v1p,p00p,p01p,p11p,l00,l10,l11,oc0,oc1,oc3,yh,pyy,pxy0,pxy1,k0,k1,inn,x0,v1,p00,p01,p11\n");
    repeat (4) @(negedge clk);
    rst_n = 1'b1;
    n_cyc = stim[0]; n_steps = stim[1]; ptr = 2; step_no = 0; cyc_total = 0;
    for (c = 0; c < n_cyc; c = c + 1) begin
        n_wr = stim[ptr]; ptr = ptr + 1;
        for (w = 0; w < n_wr; w = w + 1) begin
            wr(stim[ptr][5:0], stim[ptr+1]);  // constants + initial state
            ptr = ptr + 2;
        end
        for (t = 0; t < n_steps; t = t + 1) begin
            wr(6'd5, stim[ptr]);     // I
            wr(6'd6, stim[ptr+1]);   // Vmeas
            ptr = ptr + 2;
            @(negedge clk); start = 1'b1; cyc_start = $time;
            @(negedge clk); start = 1'b0;
            @(posedge done); @(negedge clk);
            cyc_total = cyc_total + ($time - cyc_start) / 10;
            $fwrite(fd, "%0d,%0d,%08h,%08h,%08h,%08h,%08h,%08h,%08h,%08h,%08h,%08h,%08h,%08h,%08h,%08h,%08h,%08h,%08h,%08h,%08h,%08h,%08h,%08h,%08h,%08h,%08h\n", step_no, t, dut.rf[5], dut.rf[6], dut.rf[20], dut.rf[21], dut.rf[22], dut.rf[23], dut.rf[24], dut.rf[26], dut.rf[27], dut.rf[28], dut.rf[40], dut.rf[41], dut.rf[42], dut.rf[48], dut.rf[54], dut.rf[55], dut.rf[56], dut.rf[57], dut.rf[58], dut.rf[59], dut.rf[0], dut.rf[1], dut.rf[2], dut.rf[3], dut.rf[4]);
            step_no = step_no + 1;
        end
    end
    $fclose(fd);
    $display("UKF TB done: %0d steps, average %0d clock cycles per step (start to done)", step_no, cyc_total / step_no);
    $finish;
end

endmodule
