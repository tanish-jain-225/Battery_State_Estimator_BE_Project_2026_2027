`timescale 1ns / 1ps
// ============================================================================
// mult_q6_10.v
//
// Signed Q6.10 x Q6.10 fixed-point multiplier.
//
// Format: Q6.10 = 16-bit two's complement, 6 integer bits (incl. sign),
//         10 fraction bits, scale = 2^-10 (matches Win/W/Bias/Wout/tanh.mem).
//
// The product of two Q6.10 operands is exact and fits in 32 bits with no
// rounding or precision loss:
//     a_real * b_real = (a_raw / 2^10) * (b_raw / 2^10)
//                      = (a_raw * b_raw) / 2^20
//   -> product is Q12.20 (12 integer bits, 20 fraction bits), 32-bit signed.
//
// This module is intentionally purely combinational and maps to a single
// DSP slice (e.g. Xilinx DSP48E1, 18x18 signed multiply covers 16x16 with
// margin). Pipelining/registering is left to the instantiating MAC engine
// so the FSM controls timing, matching the tanh_lut pipelining approach.
//
// Revision:
// Revision 0.01 - File Created
// Revision 0.02 - Reviewed for the full-design bug sweep: purely
//                 combinational, no logic bug found.
// ============================================================================
module mult_q6_10 (
    input  wire signed [15:0] a,       // Q6.10
    input  wire signed [15:0] b,       // Q6.10
    output wire signed [31:0] product  // Q12.20, exact
);
    assign product = a * b;
endmodule
