`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// TINY-TEST BEHAVIORAL MEMORY MODELS -- NOT SYNTHESIS IP
//
// N_IN=2, N_RES=2, T_MAX=3. Values match golden_model.py EXACTLY --
// this file and the Python model must be regenerated together if
// either changes.
//
// *** Compile these in a SEPARATE simulation fileset from the real
// win_bram/w_bram/input_bram/bias_bram/state_bram IP -- module names
// are identical on purpose (drop-in substitutes), so never let both
// exist in the same elaboration. ***
//////////////////////////////////////////////////////////////////////////////////

//----------------------------------------------------------------
// win_bram (behavioral) -- depth = N_IN*N_RES = 4
// Row-major: neuron_idx*N_IN + input_idx
//   addr 0 = neuron0,u0 = 0.5 -> 512
//   addr 1 = neuron0,u1 = 0.0 -> 0
//   addr 2 = neuron1,u0 = 0.0 -> 0
//   addr 3 = neuron1,u1 = 0.5 -> 512
//----------------------------------------------------------------
module win_bram
(
    input  wire        clka,
    input  wire        ena,
    input  wire [1:0]  addra,
    output reg  signed [15:0] douta
);
    reg signed [15:0] mem [0:3];
    initial begin
        mem[0] = 16'sd512;
        mem[1] = 16'sd0;
        mem[2] = 16'sd0;
        mem[3] = 16'sd512;
    end
    always @(posedge clka)
        if (ena) douta <= mem[addra];
endmodule

//----------------------------------------------------------------
// w_bram (behavioral) -- depth = N_RES*N_RES = 4
// Row-major: neuron_idx*N_RES + state_idx
//   addr 0 = neuron0,x0 = 0.2 -> 205
//   addr 1 = neuron0,x1 = 0.0 -> 0
//   addr 2 = neuron1,x0 = 0.0 -> 0
//   addr 3 = neuron1,x1 = 0.2 -> 205
//----------------------------------------------------------------
module w_bram
(
    input  wire        clka,
    input  wire        ena,
    input  wire [1:0]  addra,
    output reg  signed [15:0] douta
);
    reg signed [15:0] mem [0:3];
    initial begin
        mem[0] = 16'sd205;
        mem[1] = 16'sd0;
        mem[2] = 16'sd0;
        mem[3] = 16'sd205;
    end
    always @(posedge clka)
        if (ena) douta <= mem[addra];
endmodule

//----------------------------------------------------------------
// input_bram (behavioral) -- depth = N_IN*T_MAX = 2*3 = 6
// NO ena pin (matches real input_bram wrapper -- esn_top.v Rev 0.07)
// Contiguous: timestep*N_IN + input_idx
//   addr 0 = u(0)[0] = 1 -> 1024      addr 3 = u(1)[1] = 4 -> 4096
//   addr 1 = u(0)[1] = 2 -> 2048      addr 4 = u(2)[0] = 5 -> 5120
//   addr 2 = u(1)[0] = 3 -> 3072      addr 5 = u(2)[1] = 6 -> 6144
//----------------------------------------------------------------
module input_bram
(
    input  wire        clka,
    input  wire [2:0]  addra,
    output reg  signed [15:0] douta
);
    reg signed [15:0] mem [0:5];
    initial begin
        mem[0] = 16'sd1024;
        mem[1] = 16'sd2048;
        mem[2] = 16'sd3072;
        mem[3] = 16'sd4096;
        mem[4] = 16'sd5120;
        mem[5] = 16'sd6144;
    end
    always @(posedge clka)
        douta <= mem[addra];
endmodule

//----------------------------------------------------------------
// bias_bram (behavioral) -- depth = N_RES = 2, both zero
//----------------------------------------------------------------
module bias_bram
(
    input  wire        clka,
    input  wire        ena,
    input  wire        addra,
    output reg  signed [15:0] douta
);
    reg signed [15:0] mem [0:1];
    initial begin
        mem[0] = 16'sd0;
        mem[1] = 16'sd0;
    end
    always @(posedge clka)
        if (ena) douta <= mem[addra];
endmodule

//----------------------------------------------------------------
// state_bram (behavioral) -- simple dual-port, depth = N_RES = 2
// Resets to 0 -- represents x(0) = [0, 0]
//----------------------------------------------------------------
module state_bram
(
    input  wire        clka,
    input  wire        ena,
    input  wire        wea,
    input  wire        addra,
    input  wire signed [15:0] dina,

    input  wire        clkb,
    input  wire        enb,
    input  wire        addrb,
    output reg  signed [15:0] doutb
);
    reg signed [15:0] mem [0:1];
    integer i;
    initial begin
        for (i = 0; i < 2; i = i + 1)
            mem[i] = 16'sd0;
    end
    always @(posedge clka)
        if (ena && wea) mem[addra] <= dina;
    always @(posedge clkb)
        if (enb) doutb <= mem[addrb];
endmodule
