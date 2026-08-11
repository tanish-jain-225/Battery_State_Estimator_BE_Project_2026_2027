`timescale 1ns / 1ps
// ============================================================================
// mac_accum_q6_10.v
//
// MAC accumulator for the ESN neuron: sums a stream of Q6.10 x Q6.10 products
// (from mult_q6_10) in a wide, full-precision accumulator, then rounds and
// saturates the final sum back down to Q6.10 on the last term.
//
// Rationale for the wide accumulator (see project notes, Stage 4.1):
//   - Each product is exact Q12.20 (32-bit signed), no precision lost.
//   - A single neuron's pre-activation z sums up to 104 terms
//     (100 reservoir-recurrent + 4 input terms), so ACC_GUARD extra
//     integer bits are carried to guarantee no intermediate overflow
//     even in a pathological all-large-magnitude case.
//   - Only the FINAL sum is rounded/saturated back to Q6.10 (matching the
//     documented pipeline: ... -> W MAC -> Bias -> Clip +-5 -> tanh LUT).
//     Stage 4.1 measured the real pre-activation z tail at up to +-17.7,
//     comfortably inside Q6.10's +-32 range, so overflow is not expected
//     in practice, but the saturation logic is included defensively.
//
// Rounding convention: round-half-up on the 10 fractional bits being
// dropped (add 2^9 then arithmetic-shift right by 10), matching the
// "exact 1/2-LSB" rounding used for weight export (Stage 4.3) and the
// tanh LUT (Stage 4.5).
//
// Control protocol (driven by the controller FSM):
//   - Assert `clear` on the cycle of the FIRST term of a new sum
//     (accumulator starts from that term's product, not from a stale sum).
//   - Assert `en` on every cycle a valid (a,b) term should be added.
//   - Assert `last` together with `en` on the FINAL term of the sum.
//   - One cycle after `last & en`, `result_valid` pulses HIGH FOR EXACTLY
//     ONE CYCLE and `result` / `overflow` hold the rounded, saturated
//     Q6.10 output on that same cycle.
//
// Revision:
// Revision 0.01 - File Created
// Revision 0.02 - BUG FIX: result_valid was a level, not a pulse. The
//                 previous coding (`else if (last & en) result_valid <=
//                 1'b1;` with no corresponding clear) latched
//                 result_valid high permanently after the first
//                 completed MAC pass. Every accumulation after the very
//                 first one would then see mac_result_valid already
//                 high the instant S_MAC_WAIT was entered in
//                 esn_neuron, causing the consumer FSM to advance to
//                 the tanh stage before the real sum for that pass was
//                 ready (using a stale `result`/`mac_result`). Fixed by
//                 explicitly deasserting result_valid on every cycle
//                 that is not `last & en`, so it is a true single-cycle
//                 pulse. No other functional change.
// ============================================================================
module mac_accum_q6_10 #(
    parameter ACC_GUARD = 8,                  // extra integer headroom bits
    parameter ACC_WIDTH = 32 + ACC_GUARD       // 40-bit signed accumulator
) (
    input  wire                     clk,
    input  wire                     rst_n,

    input  wire                     clear,     // start a fresh sum this cycle
    input  wire                     en,        // accumulate a*b this cycle
    input  wire                     last,      // this term is the final one (with en)

    input  wire signed [15:0]       a,         // Q6.10
    input  wire signed [15:0]       b,         // Q6.10

    output reg  signed [15:0]       result,    // Q6.10, valid (1 cycle) when result_valid=1
    output reg                      overflow,  // valid on the same cycle as result_valid
    output reg                      result_valid // true single-cycle pulse
);

    // ---- product from the verified Q6.10 multiplier ------------------------
    wire signed [31:0] product;
    mult_q6_10 u_mult (
        .a(a),
        .b(b),
        .product(product)
    );

    wire signed [ACC_WIDTH-1:0] product_ext =
        {{(ACC_WIDTH-32){product[31]}}, product};   // sign-extend into accumulator width

    // ---- accumulator ---------------------------------------------------------
    reg signed [ACC_WIDTH-1:0] acc;

    wire signed [ACC_WIDTH-1:0] acc_next =
        clear ? (en ? product_ext : {ACC_WIDTH{1'b0}})
              : (en ? (acc + product_ext) : acc);

    // ---- combinational round-half-up + saturate of the NEXT accumulator value
    // (so result/overflow are ready one cycle after the final term is applied)
    wire signed [ACC_WIDTH-1:0] rounded_full = (acc_next + (1 <<< 9)) >>> 10;

    wire ovf_next = (rounded_full > $signed(33'sd32767)) ||
                    (rounded_full < $signed(-33'sd32768));

    wire signed [15:0] result_next =
        ovf_next ? (rounded_full[ACC_WIDTH-1] ? -16'sd32768 : 16'sd32767)
                 : rounded_full[15:0];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            acc          <= {ACC_WIDTH{1'b0}};
            result       <= 16'sd0;
            overflow     <= 1'b0;
            result_valid <= 1'b0;
        end else begin
            acc <= acc_next;

            if (last & en) begin
                result       <= result_next;
                overflow     <= ovf_next;
                result_valid <= 1'b1;   // pulses high this one cycle...
            end else begin
                result_valid <= 1'b0;   // ...and is explicitly cleared every other cycle
            end
        end
    end

endmodule
