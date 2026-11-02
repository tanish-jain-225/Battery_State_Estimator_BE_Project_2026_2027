`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////
// tb_ekf_core.v -- drives ekf_core with real NASA cycles and logs every
// intermediate register after each step to rtl_ekf_trace.csv, for word-by-word
// comparison against the golden model (golden_ekf_trace.csv).
//
// Needs in the simulation directory: stim.mem, ocv_lut.mem, slope_lut.mem
// (all produced by gen_vectors.py).
//
// stim.mem layout (32-bit hex words):
//   [0] n_cycles   [1] steps per cycle
//   per cycle: a, b, kcc, r0, q0, q1, r, p0, soc0, then steps x (I, Vmeas)
//////////////////////////////////////////////////////////////////////////////
module tb_ekf_core;

reg clk = 1'b0;
always #5 clk = ~clk;                       // 100 MHz simulation clock

reg rst_n = 1'b0, cfg_we = 1'b0, init = 1'b0, start = 1'b0;
reg  [4:0]         cfg_addr = 5'd0;
reg  signed [31:0] cfg_data = 32'sd0;
wire done, busy;
wire signed [31:0] soc_out;

ekf_core #(.OCV_FILE("ocv_lut.mem"), .SLOPE_FILE("slope_lut.mem")) dut (
    .clk(clk), .rst_n(rst_n), .cfg_we(cfg_we), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
    .init(init), .start(start), .done(done), .soc_out(soc_out), .busy(busy));

reg [31:0] stim [0:65535];
integer fd, n_cyc, n_steps, c, t, ptr, step_no, cyc_start, cyc_total;

task wr(input [4:0] addr, input [31:0] data);
begin
    @(negedge clk); cfg_we = 1'b1; cfg_addr = addr; cfg_data = data;
    @(negedge clk); cfg_we = 1'b0;
end
endtask

task pulse_init; begin @(negedge clk); init = 1'b1; @(negedge clk); init = 1'b0; end endtask

initial begin
    $readmemh("stim.mem", stim);
    fd = $fopen("rtl_ekf_trace.csv", "w");
    $fwrite(fd, "step,t,i,vm,x0p,v1p,p00p,p01p,p11p,idx,ocv,h0,yp,inn,ph0,ph1,s,k0,k1,x0,v1,p00,p01,p11\n");
    repeat (4) @(negedge clk);
    rst_n = 1'b1;
    n_cyc = stim[0]; n_steps = stim[1]; ptr = 2; step_no = 0; cyc_total = 0;
    for (c = 0; c < n_cyc; c = c + 1) begin
        wr(5'd22, stim[ptr+0]);  // a
        wr(5'd23, stim[ptr+1]);  // b
        wr(5'd24, stim[ptr+2]);  // kcc
        wr(5'd25, stim[ptr+3]);  // R0
        wr(5'd26, stim[ptr+4]);  // Q0
        wr(5'd27, stim[ptr+5]);  // Q1
        wr(5'd28, stim[ptr+6]);  // R
        wr(5'd31, stim[ptr+7]);  // P0
        wr(5'd0,  stim[ptr+8]);  // x0 = SOC0
        pulse_init;
        ptr = ptr + 9;
        for (t = 0; t < n_steps; t = t + 1) begin
            wr(5'd20, stim[ptr]);     // I
            wr(5'd21, stim[ptr+1]);   // Vmeas
            ptr = ptr + 2;
            @(negedge clk); start = 1'b1; cyc_start = $time;
            @(negedge clk); start = 1'b0;
            @(posedge done); @(negedge clk);
            cyc_total = cyc_total + ($time - cyc_start) / 10;
            $fwrite(fd, "%0d,%0d,%08h,%08h,%08h,%08h,%08h,%08h,%08h,%0d,%08h,%08h,%08h,%08h,%08h,%08h,%08h,%08h,%08h,%08h,%08h,%08h,%08h,%08h\n",
                step_no, t, dut.rf[20], dut.rf[21], dut.rf[5], dut.rf[6], dut.rf[7], dut.rf[8], dut.rf[9],
                dut.lut_addr, dut.rf[11], dut.rf[12], dut.rf[13], dut.rf[14], dut.rf[15], dut.rf[16],
                dut.rf[17], dut.rf[18], dut.rf[19], dut.rf[0], dut.rf[1], dut.rf[2], dut.rf[3], dut.rf[4]);
            step_no = step_no + 1;
        end
    end
    $fclose(fd);
    $display("EKF TB done: %0d steps, average %0d clock cycles per step (start to done)", step_no, cyc_total / step_no);
    $finish;
end

endmodule
