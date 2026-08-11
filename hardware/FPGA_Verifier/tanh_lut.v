`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// tanh_rom / tanh_lut
//
// Revision:
// Revision 0.01 - File Created
// Revision 0.02 - Removed the TEMPORARY DEBUG $display statements that
//                 traced valid_in/valid_out edges at the LUT boundary.
//                 Pipeline latency verified by cycle-by-cycle trace:
//                 valid_in asserted during cycle T ->
//                   valid_s1 valid at T+1 (Stage 1 register), and
//                   addr_s1  valid at T+1 (feeds tanh_rom that same cycle)
//                 tanh_rom's internal 1-cycle read registers rom_data
//                 valid at T+2, matching valid_s2 (also registered from
//                 valid_s1) which becomes valid at T+2.
//                 Stage 3 registers tanh_out/valid_out from rom_data/
//                 valid_s2 (both valid at T+2), landing at T+3.
//                 So valid_out/tanh_out are correctly aligned: 3-cycle
//                 fixed latency from valid_in to valid_out, both the
//                 valid flag and the data always land on the same edge.
//                 No functional change.
// Additional Comments:
//
//////////////////////////////////////////////////////////////////////////////////

module tanh_rom #(
    parameter ADDR_WIDTH = 13,          // covers 0..5120 (max value 5120 < 8192)
    parameter DATA_WIDTH = 16,          // Q6.10 signed
    parameter DEPTH      = 5121,        // addresses 0..5120 inclusive
    parameter MEM_FILE   = "tanh.mem"
) (
    input  wire                         clk,
    input  wire [ADDR_WIDTH-1:0]        addr,
    output reg  signed [DATA_WIDTH-1:0] data_out
);
    reg signed [DATA_WIDTH-1:0] rom [0:DEPTH-1];
    initial begin
        $readmemh(MEM_FILE, rom);
    end
    always @(posedge clk) begin
        data_out <= rom[addr];
    end
endmodule

// -----------------------------------------------------------------------
// tanh_lut: clip -> abs/sign -> ROM lookup -> sign restore
// 3-cycle fixed latency, valid_out/tanh_out land together (see rev 0.02).
// -----------------------------------------------------------------------
module tanh_lut #(
    parameter DATA_WIDTH  = 16,         // Q6.10 signed, input and output
    parameter ADDR_WIDTH  = 13,
    parameter FRAC_BITS   = 10,         // Q6.10 fractional bits (scale = 1024)
    parameter MEM_FILE    = "tanh.mem"
) (
    input  wire                          clk,
    input  wire                          rst_n,
    input  wire                          valid_in,
    input  wire signed [DATA_WIDTH-1:0]  z_in,        // Q6.10 pre-activation
    output reg                           valid_out,
    output reg  signed [DATA_WIDTH-1:0]  tanh_out     // Q6.10 tanh(z_in)
);
    // Clip boundary: +/-5.0 in Q6.10 = +/-5120
    localparam signed [DATA_WIDTH-1:0] CLIP_POS =  (5 * (1 << FRAC_BITS)); //  5120
    localparam signed [DATA_WIDTH-1:0] CLIP_NEG = -(5 * (1 << FRAC_BITS)); // -5120
    localparam MAX_ADDR = (5 * (1 << FRAC_BITS));                         //  5120

    // ---------------- Stage 1: clip, take sign/magnitude, form address ----
    reg                          sign_s1;
    reg  [ADDR_WIDTH-1:0]        addr_s1;
    reg                          valid_s1;

    wire signed [DATA_WIDTH-1:0] z_clipped;
    assign z_clipped = (z_in > CLIP_POS) ? CLIP_POS :
                        (z_in < CLIP_NEG) ? CLIP_NEG : z_in;

    wire                          sign_bit   = z_clipped[DATA_WIDTH-1];
    wire signed [DATA_WIDTH-1:0]  abs_val_ext = sign_bit ? -z_clipped : z_clipped;

    // abs_val_ext is guaranteed <= MAX_ADDR (5120), fits in ADDR_WIDTH bits
    wire [ADDR_WIDTH-1:0]         abs_val = abs_val_ext[ADDR_WIDTH-1:0];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sign_s1  <= 1'b0;
            addr_s1  <= {ADDR_WIDTH{1'b0}};
            valid_s1 <= 1'b0;
        end else begin
            sign_s1  <= sign_bit;
            addr_s1  <= abs_val;
            valid_s1 <= valid_in;
        end
    end

    // ---------------- Stage 2: ROM read (1 cycle latency inside tanh_rom) -
    wire signed [DATA_WIDTH-1:0] rom_data;

    tanh_rom #(
        .ADDR_WIDTH (ADDR_WIDTH),
        .DATA_WIDTH (DATA_WIDTH),
        .DEPTH      (MAX_ADDR + 1),
        .MEM_FILE   (MEM_FILE)
    ) u_tanh_rom (
        .clk      (clk),
        .addr     (addr_s1),
        .data_out (rom_data)
    );

    reg sign_s2;
    reg valid_s2;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sign_s2  <= 1'b0;
            valid_s2 <= 1'b0;
        end else begin
            sign_s2  <= sign_s1;
            valid_s2 <= valid_s1;
        end
    end

    // ---------------- Stage 3: sign restore, output ------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            tanh_out  <= {DATA_WIDTH{1'b0}};
            valid_out <= 1'b0;
        end else begin
            tanh_out  <= sign_s2 ? -rom_data : rom_data;
            valid_out <= valid_s2;
        end
    end

endmodule
