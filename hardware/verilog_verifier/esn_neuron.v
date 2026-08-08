`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// ESN Neuron
//
// Single neuron for Reservoir Computing
// Uses one shared MAC accumulator
// Data format : Q6.10 signed fixed point
// Range: [-5.0, 5.0] for tanh LUT
//
// Revision:
// Revision 0.01 - File Created
// Revision 0.02 - Consolidated MAC accumulation (Win.u and W.x share one
//                 continuous accumulation pass; single S_MAC_WAIT instead
//                 of two).
// Revision 0.03 - Removed mac_a/mac_b register stage; mac_a/mac_b are
//                 combinational, muxed off win_data/u_data or w_data/x_data.
// Revision 0.04-0.05 - TEMPORARY DEBUG prints around S_TANH_START /
//                 S_TANH_WAIT (removed in 0.07, see below).
// Revision 0.06 - S_DONE confirmed to operate as a normal 1-cycle pulse
//                 back to S_IDLE (no functional change from 0.01/0.02).
// Revision 0.07 - Removed all TEMPORARY DEBUG $display statements from
//                 0.04/0.05 now that tanh_valid_out reachability/timing
//                 has been confirmed (see tanh_lut.v revision notes for
//                 the equivalent cleanup there). No functional change.
//                 Note: the actual data-corruption bug in this pipeline
//                 was NOT in this module -- it was a sticky (non-
//                 pulsing) result_valid in mac_accum_q6_10.v, which made
//                 S_MAC_WAIT below advance immediately on every neuron
//                 after the first, using a stale mac_result. See
//                 mac_accum_q6_10.v revision 0.02 for the fix.
// Revision 0.08 - Added neuron_idx and buf_sel as new INPUT ports (both
//                 sourced from esn_top -- neuron_idx already existed
//                 there as the controller's per-pass neuron index,
//                 buf_sel already existed there as the ping-pong state
//                 buffer select). Neither identifier previously existed
//                 inside this module's scope. Added purely so the debug
//                 $display below (Rev 0.09) can report which neuron and
//                 which ping-pong buffer a given MAC/tanh result belongs
//                 to; both are pass-through wires with no effect on any
//                 existing datapath or FSM logic in this module.
// Revision 0.09 - Added a golden-model debug $display inside S_TANH_WAIT,
//                 gated on tanh_valid_out, immediately after x_next <=
//                 tanh_output. Prints TIME, PASSBUF (buf_sel), NEURON
//                 (neuron_idx), MAC (mac_result), BIAS, SUM
//                 (neuron_sum_w), TANH_IN (tanh_input), and TANH_OUT.
//                 Intentionally prints tanh_output rather than x_next:
//                 x_next <= tanh_output is a non-blocking assignment, so
//                 x_next still holds the PREVIOUS neuron's value at the
//                 time this $display executes on the same edge;
//                 tanh_output already holds the value that will become
//                 x_next once this edge settles. No functional/datapath
//                 change -- simulation-only visibility.
// Revision 0.10 - Added CSV logging alongside the existing Rev 0.09
//                 $display, writing the same fields (time, buf_sel,
//                 neuron_idx, mac_result, bias, neuron_sum_w,
//                 tanh_input, tanh_output) to vivado_esn_results.csv
//                 for automated golden-model comparison.
//                   - Added `integer csv_file` (module-scope, declared
//                     alongside the other debug/id signals).
//                   - Added a top-level `initial` block that opens the
//                     file and writes the CSV header exactly once, at
//                     time 0 (before rst_n deasserts). This is safe
//                     because esn_neuron is instantiated exactly once
//                     in this design (as u_neuron inside esn_top); if
//                     that ever changes to multiple instances, this
//                     initial block would need to move to a single
//                     shared owner (e.g. esn_top) instead, or each
//                     instance will clobber the same file.
//                   - Added a single $fwrite call inside S_TANH_WAIT,
//                     immediately below the existing $display, using
//                     the identical argument list/order (time, buf_sel,
//                     neuron_idx, mac_result, bias, neuron_sum_w,
//                     tanh_input, tanh_output) so the CSV and the
//                     console log can never drift apart.
//                   - No $fclose is issued: this is plain Verilog (not
//                     SystemVerilog), so there is no `final` block
//                     available inside this module to hook a clean
//                     close on $finish, and esn_neuron itself has no
//                     other simulation-end event visible to it. Left
//                     open deliberately -- simulators (incl. Vivado/
//                     xsim) flush and close open file descriptors on
//                     $finish, so no data is lost. If a guaranteed
//                     explicit close is required, it belongs in the
//                     testbench (tb_esn_top.v) via $fclose on this same
//                     descriptor instead, since that module owns the
//                     actual simulation-end event.
//                 No functional/datapath change -- FSM, ports, and all
//                 existing logic are unmodified.
// Additional Comments:
//
//////////////////////////////////////////////////////////////////////////////////

module esn_neuron
#(
    parameter DW    = 16,
    parameter N_IN  = 4,
    parameter N_RES = 100
)
(
    input  wire                     clk,
    input  wire                     rst_n,

    //--------------------------------------------------
    // Control
    //--------------------------------------------------
    input  wire                     start,  // Must be 1-cycle pulse
    output reg                      done,

    //--------------------------------------------------
    // Debug / identification (Rev 0.08)
    //--------------------------------------------------
    // Pass-through from esn_top: neuron_idx already exists there
    // (driven by reservoir_controller), buf_sel already exists there
    // (the ping-pong state buffer select register). Neither carries
    // any datapath function inside esn_neuron itself -- both exist
    // solely so the Rev 0.09 debug $display can report which neuron
    // and which ping-pong buffer a given result belongs to.
    //--------------------------------------------------
    input  wire [$clog2(N_RES)-1:0] neuron_idx,
    input  wire                     buf_sel,

    //--------------------------------------------------
    // Win memory
    //--------------------------------------------------
    output reg  [$clog2(N_IN)-1:0]  win_addr,
    input  wire signed [DW-1:0]     win_data,

    //--------------------------------------------------
    // Input vector u
    //--------------------------------------------------
    output reg  [$clog2(N_IN)-1:0]  u_addr,
    input  wire signed [DW-1:0]     u_data,

    //--------------------------------------------------
    // Reservoir weight memory
    //--------------------------------------------------
    output reg  [$clog2(N_RES)-1:0] w_addr,
    input  wire signed [DW-1:0]     w_data,

    //--------------------------------------------------
    // Reservoir state vector
    //--------------------------------------------------
    output reg  [$clog2(N_RES)-1:0] x_addr,
    input  wire signed [DW-1:0]     x_data,

    //--------------------------------------------------
    // Bias
    //--------------------------------------------------
    input wire signed [DW-1:0]      bias,

    //--------------------------------------------------
    // Output
    //--------------------------------------------------
    output reg signed [DW-1:0]      x_next,
    output reg                      overflow
);

/////////////////////////////////////////////////////////
// FSM States
/////////////////////////////////////////////////////////

localparam S_IDLE          = 4'd0;

// Win.u computation
localparam S_WIN_ADDR      = 4'd1;
localparam S_WIN_READ      = 4'd2;
localparam S_WIN_MAC       = 4'd3;
localparam S_WIN_NEXT      = 4'd4;

// W.x computation (continues accumulating into the same MAC pass)
localparam S_W_ADDR        = 4'd5;
localparam S_W_READ        = 4'd6;
localparam S_W_MAC         = 4'd7;
localparam S_W_NEXT        = 4'd8;

// Post processing
localparam S_MAC_WAIT      = 4'd9;   // wait for final result_valid; add bias + clip here
localparam S_TANH_START    = 4'd10;
localparam S_TANH_WAIT     = 4'd11;
localparam S_DONE          = 4'd12;

reg [3:0] state;

/////////////////////////////////////////////////////////
// Parameters for clipping
/////////////////////////////////////////////////////////

localparam signed [17:0] CLIP_MAX = 18'sd5120;  // 5.0 in Q6.10
localparam signed [17:0] CLIP_MIN = -18'sd5120; // -5.0 in Q6.10

/////////////////////////////////////////////////////////
// Counters
/////////////////////////////////////////////////////////

reg [$clog2(N_IN)-1:0]   win_count;
reg [$clog2(N_RES)-1:0]  res_count;

/////////////////////////////////////////////////////////
// MAC Interface
/////////////////////////////////////////////////////////

reg                     mac_clear;
reg                     mac_en;
reg                     mac_last;

// mac_a/mac_b are purely combinational -- fed straight from the BRAM
// read ports, no extra register stage. Selected by FSM phase: states
// S_WIN_ADDR..S_WIN_NEXT (< S_W_ADDR) use Win.u operands, states
// S_W_ADDR..S_W_NEXT use W.x operands. The mux value is only consumed
// while mac_en is high (asserted from S_WIN_MAC/S_W_MAC), so its value
// in S_IDLE/S_MAC_WAIT/etc. is irrelevant.
wire                    win_phase = (state < S_W_ADDR);

wire signed [15:0]      mac_a = win_phase ? win_data : w_data;
wire signed [15:0]      mac_b = win_phase ? u_data   : x_data;

wire signed [15:0]      mac_result;
wire                    mac_overflow;
wire                    mac_result_valid;

/////////////////////////////////////////////////////////
// Bias-add + clip (combinational, consumed only in S_MAC_WAIT
// when mac_result_valid is asserted, i.e. once mac_result holds
// the full Win.u + W.x running sum)
/////////////////////////////////////////////////////////

wire signed [17:0] mac_result_ext = {{2{mac_result[15]}}, mac_result};
wire signed [17:0] bias_ext       = {{2{bias[15]}}, bias};
wire signed [17:0] neuron_sum_w   = mac_result_ext + bias_ext;

/////////////////////////////////////////////////////////
// tanh Interface
/////////////////////////////////////////////////////////

reg                     tanh_valid_in;
reg signed [15:0]       tanh_input;

wire                    tanh_valid_out;
wire signed [15:0]      tanh_output;

/////////////////////////////////////////////////////////
// CSV debug logging (Rev 0.10)
/////////////////////////////////////////////////////////

integer csv_file;

initial
begin
    csv_file = $fopen("vivado_esn_results.csv", "w");
    $fwrite(csv_file,
            "time,passbuf,neuron,mac,bias,sum,tanh_in,tanh_out\n");
end

/////////////////////////////////////////////////////////
// Shared MAC Accumulator
/////////////////////////////////////////////////////////

mac_accum_q6_10 u_mac
(
    .clk(clk),
    .rst_n(rst_n),

    .clear(mac_clear),
    .en(mac_en),
    .last(mac_last),

    .a(mac_a),
    .b(mac_b),

    .result(mac_result),
    .overflow(mac_overflow),
    .result_valid(mac_result_valid)
);

/////////////////////////////////////////////////////////
// tanh LUT
/////////////////////////////////////////////////////////

tanh_lut u_tanh
(
    .clk(clk),
    .rst_n(rst_n),

    .valid_in(tanh_valid_in),
    .z_in(tanh_input),

    .valid_out(tanh_valid_out),
    .tanh_out(tanh_output)
);

/////////////////////////////////////////////////////////
// Main FSM
/////////////////////////////////////////////////////////

always @(posedge clk or negedge rst_n)
begin

    if(!rst_n)
    begin

        //------------------------------------------
        // FSM
        //------------------------------------------

        state <= S_IDLE;

        //------------------------------------------
        // Outputs
        //------------------------------------------

        done <= 1'b0;
        overflow <= 1'b0;
        x_next <= 16'sd0;

        //------------------------------------------
        // Memory Addresses
        //------------------------------------------

        win_addr <= 0;
        u_addr   <= 0;
        w_addr   <= 0;
        x_addr   <= 0;

        //------------------------------------------
        // Counters
        //------------------------------------------

        win_count <= 0;
        res_count <= 0;

        //------------------------------------------
        // MAC Control
        //------------------------------------------

        mac_clear <= 1'b0;
        mac_en    <= 1'b0;
        mac_last  <= 1'b0;

        //------------------------------------------
        // tanh
        //------------------------------------------

        tanh_valid_in <= 1'b0;
        tanh_input    <= 16'sd0;

    end

    else
    begin

        //------------------------------------------
        // Default pulse signals
        //------------------------------------------

        done <= 1'b0;

        mac_clear <= 1'b0;
        mac_en    <= 1'b0;
        mac_last  <= 1'b0;

        tanh_valid_in <= 1'b0;

        //------------------------------------------
        // FSM
        //------------------------------------------

        case(state)

        //////////////////////////////////////////////////////
        // IDLE
        //////////////////////////////////////////////////////

        S_IDLE:
        begin

            if(start)
            begin

                //----------------------------------
                // Prepare for a single continuous
                // MAC pass covering both Win.u and
                // W.x -- no clear/restart in between
                //----------------------------------

                win_count <= 0;
                overflow <= 1'b0;

                state <= S_WIN_ADDR;

            end

        end

        //////////////////////////////////////////////////////
        // WIN ADDR
        //////////////////////////////////////////////////////

        S_WIN_ADDR:
        begin

            win_addr <= win_count;
            u_addr   <= win_count;

            state <= S_WIN_READ;

        end

        //////////////////////////////////////////////////////
        // WIN READ
        //////////////////////////////////////////////////////

        S_WIN_READ:
        begin

            // BRAM data becomes valid this cycle
            state <= S_WIN_MAC;

        end

        //////////////////////////////////////////////////////
        // WIN MAC
        //////////////////////////////////////////////////////

        S_WIN_MAC:
        begin

            // mac_a/mac_b are combinational (win_data/u_data via
            // the win_phase mux) -- no register capture needed here.

            mac_en    <= 1'b1;
            mac_clear <= (win_count == 0);  // clear once, on the very first product
            mac_last  <= 1'b0;              // never last here -- W.x MACs follow

            state <= S_WIN_NEXT;

        end

        //////////////////////////////////////////////////////
        // WIN NEXT
        //////////////////////////////////////////////////////

        S_WIN_NEXT:
        begin

            mac_en <= 1'b0;

            if(win_count == N_IN-1)
            begin
                // Win.u done -- roll straight into W.x on the SAME
                // accumulation pass, no clear/wait in between
                res_count <= 0;
                state <= S_W_ADDR;
            end
            else
            begin
                win_count <= win_count + 1;
                state <= S_WIN_ADDR;
            end

        end

        //////////////////////////////////////////////////////
        // W ADDR
        //////////////////////////////////////////////////////

        S_W_ADDR:
        begin

            w_addr <= res_count;
            x_addr <= res_count;

            state <= S_W_READ;

        end

        //////////////////////////////////////////////////////
        // W READ
        //////////////////////////////////////////////////////

        S_W_READ:
        begin

            // BRAM data becomes valid this cycle
            state <= S_W_MAC;

        end

        //////////////////////////////////////////////////////
        // W MAC
        //////////////////////////////////////////////////////

        S_W_MAC:
        begin

            // mac_a/mac_b are combinational (w_data/x_data via
            // the win_phase mux) -- no register capture needed here.

            mac_en    <= 1'b1;
            mac_clear <= 1'b0;                     // never re-clear -- continuing the same pass
            mac_last  <= (res_count == N_RES-1);   // last product of the ENTIRE neuron

            state <= S_W_NEXT;

        end

        //////////////////////////////////////////////////////
        // W NEXT
        //////////////////////////////////////////////////////

        S_W_NEXT:
        begin

            mac_en <= 1'b0;

            if(res_count == N_RES-1)
                state <= S_MAC_WAIT;   // wait for the single final result_valid
            else
            begin
                res_count <= res_count + 1;
                state <= S_W_ADDR;
            end

        end

        //////////////////////////////////////////////////////
        // MAC WAIT  (Win.u + W.x fully accumulated here)
        //////////////////////////////////////////////////////

        S_MAC_WAIT:
        begin

            // result_valid is now a genuine 1-cycle pulse (see
            // mac_accum_q6_10.v rev 0.02), so this correctly waits
            // for THIS neuron's own final MAC result every time --
            // not just the first neuron.
            if(mac_result_valid)
            begin

                if(mac_overflow)
                    overflow <= 1'b1;

                //----------------------------------
                // Add bias + clip, merged into this
                // same cycle (neuron_sum_w is combi-
                // national off mac_result + bias)
                //----------------------------------

                if(neuron_sum_w > CLIP_MAX)
                    tanh_input <= CLIP_MAX[15:0];
                else if(neuron_sum_w < CLIP_MIN)
                    tanh_input <= CLIP_MIN[15:0];
                else
                    tanh_input <= neuron_sum_w[15:0];

                state <= S_TANH_START;

            end

        end

        //////////////////////////////////////////////////////
        // TANH START
        //////////////////////////////////////////////////////

        S_TANH_START:
        begin

            tanh_valid_in <= 1'b1;

            state <= S_TANH_WAIT;

        end

        //////////////////////////////////////////////////////
        // TANH WAIT
        //////////////////////////////////////////////////////

        S_TANH_WAIT:
        begin

            if (tanh_valid_out)
            begin

                //------------------------------------------------------
                // Sanity-check print (temporary) -- confirms this
                // branch is actually reached in simulation, i.e. that
                // tanh_valid_out really does pulse and S_TANH_WAIT is
                // really entered/exited as expected. If "DISPLAY HIT"
                // never appears in the sim log, the debug prints below
                // are not the issue -- this branch simply isn't firing,
                // meaning the wrong simulation/build is being examined,
                // or tanh_valid_out/S_TANH_WAIT reachability itself is
                // broken.
                //------------------------------------------------------
                $display("DISPLAY HIT");

                //------------------------------------------------------
                // Debug print for Golden Model comparison (Rev 0.09)
                //------------------------------------------------------
                // NOTE: prints tanh_output, NOT x_next. x_next <=
                // tanh_output below is a non-blocking assignment, so
                // x_next still holds the PREVIOUS neuron's value at
                // the point this $display executes within the same
                // always-block evaluation; tanh_output already holds
                // the value that will land in x_next once this edge
                // settles.
                //------------------------------------------------------
                $display(
                    "TIME=%0t PASSBUF=%0d NEURON=%0d MAC=%h BIAS=%h SUM=%h TANH_IN=%h TANH_OUT=%h",
                    $time,
                    buf_sel,
                    neuron_idx,
                    mac_result,
                    bias,
                    neuron_sum_w,
                    tanh_input,
                    tanh_output
                );

                //------------------------------------------------------
                // CSV logging for automated golden-model comparison
                // (Rev 0.10). Same fields, same order, same source
                // signals as the $display immediately above -- kept
                // side-by-side deliberately so the console log and the
                // CSV can never diverge.
                //------------------------------------------------------
                $fwrite(csv_file,
                        "%0t,%0d,%0d,%h,%h,%h,%h,%h\n",
                        $time,
                        buf_sel,
                        neuron_idx,
                        mac_result,
                        bias,
                        neuron_sum_w,
                        tanh_input,
                        tanh_output
                );

                x_next <= tanh_output;
                state  <= S_DONE;

            end

        end

        //////////////////////////////////////////////////////
        // DONE
        //////////////////////////////////////////////////////

        S_DONE:
        begin

            done  <= 1'b1;
            state <= S_IDLE;

        end

        endcase

    end

end

/////////////////////////////////////////////////////////
// Simulation Assertions (only for simulation)
/////////////////////////////////////////////////////////

`ifdef SIMULATION

    // Track start pulse
    reg start_d1;
    always @(posedge clk) start_d1 <= start;

    // Check start is 1-cycle pulse
    always @(posedge clk) begin
        if (!rst_n) begin
            // Reset state
        end else begin
            if (start && start_d1) begin
                $error("ERROR: start must be a 1-cycle pulse");
            end
        end
    end

    // Check result_valid timing (only when not in reset).
    // There is a single "last MAC issued" event per neuron -- the
    // final W MAC at res_count == N_RES-1 -- since Win.u and W.x
    // share one continuous accumulation pass.
    reg mac_last_issued;

    always @(posedge clk) begin
        if (!rst_n) begin
            mac_last_issued <= 1'b0;
        end else begin
            // Track when we issue the last MAC of the whole neuron
            if (state == S_W_MAC && res_count == N_RES-1) begin
                mac_last_issued <= 1'b1;
            end

            // Check result_valid fires after the final MAC
            if (mac_last_issued) begin
                if (!mac_result_valid) begin
                    $warning("WARNING: mac_result_valid not detected after final W MAC");
                end
                mac_last_issued <= 1'b0;
            end

            // Additional check enabled by the result_valid pulse fix:
            // result_valid should NEVER be high while NOT immediately
            // following a last&en MAC term. If this ever fires, the
            // sticky-result_valid class of bug has regressed.
            if (mac_result_valid && !mac_last_issued && state != S_MAC_WAIT) begin
                $warning("WARNING: mac_result_valid asserted outside S_MAC_WAIT -- check for a regression of the sticky result_valid bug");
            end
        end
    end

`endif

endmodule
