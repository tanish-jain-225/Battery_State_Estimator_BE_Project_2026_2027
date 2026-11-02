`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// tb_esn_top_tiny -- N_IN=2, N_RES=2, T_MAX=3 bit-exact verification test
//
// Uses the REAL esn_top/esn_neuron/reservoir_controller/address_generator/
// mac_accum_q6_10/mult_q6_10/tanh_lut RTL (unmodified, same files as the
// N_IN=4/N_RES=100 design), compiled against the BEHAVIORAL memory models
// in tiny_bram_models.v instead of the real BRAM IP.
//
// tanh_lut.v still reads the REAL tanh.mem via $readmemh -- add tanh.mem
// to this simulation fileset too, same file used by the full design.
//
// Purpose: verify (a) the newly regenerated Win/W/bias produce correct
// MAC/tanh output, and (b) timestep-dependent input addressing is correct
// under THREE DISTINCT inputs u(0),u(1),u(2) -- not just the fixed-input
// case. Compare the vivado_esn_results.csv this run produces (written by
// esn_neuron.v itself) against golden_results.csv from golden_model.py --
// they should match column-for-column, row-for-row.
//////////////////////////////////////////////////////////////////////////////////
module tb_esn_top_tiny;

parameter DW    = 16;
parameter N_IN  = 2;
parameter N_RES = 2;
parameter T_MAX = 3;

localparam T_STEPS = 3;

reg clk = 0;
always #5 clk = ~clk;

reg rst_n;
reg start;
wire done;

esn_top
#(
    .DW(DW),
    .N_IN(N_IN),
    .N_RES(N_RES),
    .T_MAX(T_MAX)
)
dut
(
    .clk   (clk),
    .rst_n (rst_n),
    .start (start),
    .done  (done)
);

// Report u_addr each time it's driven, and x_next as each neuron
// finishes -- lets you sanity-check the console log directly against
// golden_results.csv even before diffing the actual CSV files.
always @(posedge clk)
begin
    if (dut.u_neuron.state == 4'd1)  // S_WIN_ADDR
        $display("[%0t] timestep=%0d neuron_idx=%0d u_addr=%0d",
                 $time, dut.timestep, dut.neuron_idx, dut.u_addr);
end

always @(posedge clk)
begin
    if (dut.u_neuron.done)
        $display("[%0t] timestep=%0d neuron_idx=%0d x_next=%0d (%.4f real)",
                 $time, dut.timestep, dut.neuron_idx, dut.x_next,
                 $itor(dut.x_next) / 1024.0);
end

integer t;

initial
begin
    rst_n = 0;
    start = 0;
    #100;
    rst_n = 1;
    #20;

    for (t = 0; t < T_STEPS; t = t + 1)
    begin
        $display("");
        $display("======================================");
        $display("PASS %0d : Compute x(%0d) using u(%0d)", t+1, t+1, t);
        $display("======================================");

        start = 1;
        #10;
        start = 0;

        wait(done);
        $display("[%0t] PASS %0d COMPLETE", $time, t+1);

        wait(!done);
        #50;
    end

    $display("");
    $display("======================================");
    $display("TEST COMPLETED -- N_IN=2/N_RES=2/T=3 bit-exact check");
    $display("Compare vivado_esn_results.csv against golden_results.csv");
    $display("EXPECTED (from golden_model.py, Q6.10 quantized real value):");
    $display("  x(1) = [0.4619, 0.7617]");
    $display("  x(2) = [0.9209, 0.9736]");
    $display("  x(3) = [0.9912, 0.9971]");
    $display("======================================");

    #100;
    $finish;
end

endmodule
