`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////
// esn_ram.v -- portable simple-dual-port RAM (1 write port, 1 read port)
//
// Vendor-neutral replacement for the Xilinx Block Memory Generator IPs that
// the first ESN prototype used. Standard inference template: Vivado maps it
// to block RAM (READ_LAT = 2 uses the BRAM output register), other tools map
// it to their own RAM primitives.
//
//   write : we / waddr / wdata           (synchronous)
//   read  : re / raddr -> rdata          READ_LAT cycles after raddr
//           READ_LAT = 1 : rdata valid the cycle after raddr
//           READ_LAT = 2 : rdata valid two cycles after raddr (output register)
//   re low holds the first read stage (same behaviour as an IP read enable).
//   Reading an address being written in the same cycle returns the OLD data.
//
//   INIT_FILE : optional $readmemh file (empty string = zero-initialised)
//////////////////////////////////////////////////////////////////////////////
module esn_ram #(
    parameter DEPTH     = 256,
    parameter WIDTH     = 16,
    parameter READ_LAT  = 2,
    parameter INIT_FILE = ""
)(
    input  wire                       clk,
    input  wire                       we,
    input  wire [$clog2(DEPTH)-1:0]   waddr,
    input  wire [WIDTH-1:0]           wdata,
    input  wire                       re,
    input  wire [$clog2(DEPTH)-1:0]   raddr,
    output wire [WIDTH-1:0]           rdata
);
    reg [WIDTH-1:0] mem [0:DEPTH-1];
    reg [WIDTH-1:0] d1, d2;
    integer i;
    initial begin
        for (i = 0; i < DEPTH; i = i + 1) mem[i] = {WIDTH{1'b0}};
        if (INIT_FILE != "") $readmemh(INIT_FILE, mem);
        d1 = {WIDTH{1'b0}};
        d2 = {WIDTH{1'b0}};
    end
    always @(posedge clk) begin
        if (we) mem[waddr] <= wdata;
        if (re) d1 <= mem[raddr];
        d2 <= d1;
    end
    assign rdata = (READ_LAT == 1) ? d1 : d2;
endmodule


// esn_ram_dist: same behaviour as esn_ram, mapped to LUT RAM (small per-lane memories of esn_core_fast)
module esn_ram_dist #(
    parameter DEPTH     = 256,
    parameter WIDTH     = 16,
    parameter READ_LAT  = 2
)(
    input  wire                       clk,
    input  wire                       we,
    input  wire [$clog2(DEPTH)-1:0]   waddr,
    input  wire [WIDTH-1:0]           wdata,
    input  wire                       re,
    input  wire [$clog2(DEPTH)-1:0]   raddr,
    output wire [WIDTH-1:0]           rdata
);
    (* ram_style = "distributed" *) reg [WIDTH-1:0] mem [0:DEPTH-1];
    reg [WIDTH-1:0] d1, d2;
    integer i;
    initial begin
        for (i = 0; i < DEPTH; i = i + 1) mem[i] = {WIDTH{1'b0}};
        d1 = {WIDTH{1'b0}};
        d2 = {WIDTH{1'b0}};
    end
    always @(posedge clk) begin
        if (we) mem[waddr] <= wdata;
        if (re) d1 <= mem[raddr];
        d2 <= d1;
    end
    assign rdata = (READ_LAT == 1) ? d1 : d2;
endmodule
