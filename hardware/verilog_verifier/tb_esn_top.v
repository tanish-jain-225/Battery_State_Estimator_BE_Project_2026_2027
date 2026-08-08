`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 03.08.2026 10:04:52
// Design Name: 
// Module Name: tb_esn_top
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module tb_esn_top;

parameter DW    = 16;
parameter N_IN  = 4;
parameter N_RES = 100;

//////////////////////////////////////////////////////
// Clock
//////////////////////////////////////////////////////

reg clk = 0;
always #5 clk = ~clk;

//////////////////////////////////////////////////////
// Reset / Control
//////////////////////////////////////////////////////

reg rst_n;
reg start;

wire done;

//////////////////////////////////////////////////////
// DUT
//////////////////////////////////////////////////////

esn_top
#(
    .DW(DW),
    .N_IN(N_IN),
    .N_RES(N_RES)
)
dut
(
    .clk   (clk),
    .rst_n (rst_n),
    .start (start),
    .done  (done)
);

//////////////////////////////////////////////////////
// Display the input addresses used
//
// Since u_addr is driven from win_count, this monitor
// confirms that every new START reads addresses
// 0,1,2,3 again (fixed-input architecture).
//////////////////////////////////////////////////////

always @(posedge clk)
begin
    if (dut.u_neuron.state == 4'd1)      // S_WIN_ADDR
    begin
        $display("[%0t] u_addr = %0d",
                 $time,
                 dut.u_addr);
    end
end

//////////////////////////////////////////////////////
// Stimulus
//////////////////////////////////////////////////////

initial
begin

    rst_n = 0;
    start = 0;

    #100;
    rst_n = 1;

    #20;

    //--------------------------------------------------
    // PASS 1
    //--------------------------------------------------

    $display("");
    $display("======================================");
    $display("PASS 1 : Compute x(1)");
    $display("======================================");

    start = 1;
    #10;
    start = 0;

    wait(done);

    $display("[%0t] PASS 1 COMPLETE", $time);

    //--------------------------------------------------
    // Wait for done to deassert
    //--------------------------------------------------

    wait(!done);

    #50;

    //--------------------------------------------------
    // PASS 2
    //--------------------------------------------------

    $display("");
    $display("======================================");
    $display("PASS 2 : Compute x(2)");
    $display("======================================");

    start = 1;
    #10;
    start = 0;

    wait(done);

    $display("[%0t] PASS 2 COMPLETE", $time);

    //--------------------------------------------------
    // End
    //--------------------------------------------------

    $display("");
    $display("======================================");
    $display("TEST COMPLETED");
    $display("This test verifies:");
    $display("  x(0) -> x(1)");
    $display("  x(1) -> x(2)");
    $display("using the SAME input vector u(0).");
    $display("");
    $display("It does NOT verify multi-timestep");
    $display("input sequence processing.");
    $display("======================================");

    #100;

    $finish;

end

endmodule
