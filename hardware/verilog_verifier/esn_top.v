`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: Vivekanand Education Society's Institute Of Technology
// Engineer: Nambiar Akshay
// 
// Design Name: 
// Module Name: esn_top
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Revision 0.02 - Fixed floating u_data/x_data/bias, removed duplicate
//                 timescale, noted x_next currently unused pending
//                 state_bram integration
// Revision 0.03 - Fixed state_bram read/write address aliasing bug:
//                 switched state_bram to simple dual-port so the
//                 write-back address (neuron_idx) is independent of
//                 the read-sweep address (res_count / x_addr)
// Revision 0.04 - Removed intermediate x_mem_addr/x_write_addr wires;
//                 neuron_idx and x_addr now connect directly to the
//                 state_bram write/read ports
// Revision 0.05 - Switched state memory to ping-pong (double buffer):
//                 single-buffer design let neuron i's write-back be
//                 visible to neuron i+1 within the same pass, which
//                 is a Gauss-Seidel update rather than the required
//                 synchronous x(k+1) = tanh(W*x(k) + Win*u + b) rule.
//                 Two state_bram instances now hold x(k) and x(k+1);
//                 buf_sel toggles which is old/read vs new/write once
//                 per full N_RES-neuron pass.
// Revision 0.06 - Wired up input_bram for u_data.
// Revision 0.07 - Removed the .ena(1'b1) port connection from the
//                 input_bram instantiation (wrapper has no enable pin).
// Revision 0.08 - Wired up bias_bram for bias, addressed by neuron_idx.
// Revision 0.09 - BUGFIX: removed the .x_addr/.x_mem_addr connections
//                 from address_generator -- x_addr was multi-driven
//                 (address_generator AND esn_neuron both drove it).
//                 esn_neuron is now the sole owner of x_addr.
// Revision 0.10 - BUGFIX: buf_sel was toggling on the raw controller
//                 `done` signal, which is a LEVEL (high for as long as
//                 the controller sits in FINISHED, i.e. for as long as
//                 the external `start` input is held asserted after
//                 the pass completes -- see reservoir_controller.v,
//                 FINISHED stays entered until `!start`). If `start`
//                 is held for more than one cycle after completion,
//                 `done` was staying high for multiple cycles, and
//                 `buf_sel <= ~buf_sel` was firing on EVERY one of
//                 those cycles instead of exactly once per pass --
//                 silently corrupting the ping-pong scheme (which
//                 buffer is old/new for the next pass would then
//                 depend on how many extra cycles `start` happened to
//                 be held for, not on anything architecturally
//                 meaningful). Unlike `neuron_start`, there was no
//                 guarantee anywhere that the top-level `start`/`done`
//                 are single-cycle pulses.
//                 Fixed by locally edge-detecting `done` in this
//                 module (done_pulse = done & ~done_d1) and toggling
//                 buf_sel on that pulse instead of on the raw level.
//                 This makes the swap correct exactly once per pass
//                 regardless of how long start/done happen to be held
//                 by whatever drives this module. No other functional
//                 change; the buf_sel-driven write/read gating and the
//                 x_data mux (both already self-consistent and
//                 verified against the buf_sel==0/1 buffer-role
//                 convention documented below) are unchanged.
// Revision 0.11 - Connected neuron_idx and buf_sel (both already
//                 existed as wires/reg in this module) into two new
//                 input ports on esn_neuron, added there so its
//                 internal debug $display (see esn_neuron.v Rev
//                 0.08/0.09) can report which neuron index and which
//                 ping-pong buffer a given MAC/tanh result belongs to.
//                 Both are pure pass-throughs of signals that already
//                 existed in this module for other purposes
//                 (neuron_idx already fed address_generator/bias_bram/
//                 state_bram write ports; buf_sel already gated the
//                 state_bram read/write ports and the x_data mux) --
//                 no new logic, no change to any existing datapath.
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////
// ESN Top Module
//////////////////////////////////////////////////////////////////////////////////

module esn_top
#(
    parameter DW    = 16,
    parameter N_IN  = 4,
    parameter N_RES = 100
)
(
    input  wire clk,
    input  wire rst_n,
    input  wire start,

    output wire done
);

////////////////////////////////////////////////////////////
// Controller Signals
////////////////////////////////////////////////////////////

wire neuron_start;
wire neuron_done;

wire reservoir_busy;
wire store_en;

wire [$clog2(N_RES)-1:0] neuron_idx;

////////////////////////////////////////////////////////////
// Neuron Interface
////////////////////////////////////////////////////////////

wire signed [DW-1:0] x_next;
wire overflow;

////////////////////////////////////////////////////////////
// Logical Addresses (Generated by ESN Neuron)
////////////////////////////////////////////////////////////

wire [$clog2(N_IN)-1:0]  win_addr;
wire [$clog2(N_IN)-1:0]  u_addr;

wire [$clog2(N_RES)-1:0] w_addr;
wire [$clog2(N_RES)-1:0] x_addr;   // driven solely by esn_neuron -- see Rev 0.09

////////////////////////////////////////////////////////////
// Data Buses
////////////////////////////////////////////////////////////

wire signed [DW-1:0] win_data;
wire signed [DW-1:0] u_data;

wire signed [DW-1:0] w_data;
wire signed [DW-1:0] x_data;

wire signed [DW-1:0] bias;

////////////////////////////////////////////////////////////
// Physical Memory Addresses
////////////////////////////////////////////////////////////

wire [$clog2(N_IN*N_RES)-1:0]  win_base_addr;
wire [$clog2(N_RES*N_RES)-1:0] w_base_addr;

wire [$clog2(N_IN*N_RES)-1:0]  win_mem_addr;
wire [$clog2(N_RES*N_RES)-1:0] w_mem_addr;

////////////////////////////////////////////////////////////
// Address Generation
////////////////////////////////////////////////////////////

assign win_mem_addr = win_base_addr + win_addr;
assign w_mem_addr   = w_base_addr + w_addr;

////////////////////////////////////////////////////////////
// Reservoir Controller
////////////////////////////////////////////////////////////

reservoir_controller
#(
    .N_RES(N_RES)
)
u_controller
(
    .clk(clk),
    .rst_n(rst_n),

    .start(start),

    .done(done),

    .reservoir_busy(reservoir_busy),

    .neuron_start(neuron_start),
    .neuron_done(neuron_done),

    .neuron_idx(neuron_idx),

    .store_en(store_en)
);

////////////////////////////////////////////////////////////
// Address Generator
////////////////////////////////////////////////////////////
// Rev 0.09: only supplies the per-neuron BASE addresses
// (win_base_addr, w_base_addr). It no longer drives x_addr --
// esn_neuron already generates x_addr itself (x_addr <= res_count;
// in S_W_ADDR, exactly mirroring w_addr).
////////////////////////////////////////////////////////////

address_generator
#(
    .N_IN(N_IN),
    .N_RES(N_RES)
)
u_addr_gen
(
    .neuron_idx(neuron_idx),

    .win_base_addr(win_base_addr),
    .w_base_addr(w_base_addr)
);

////////////////////////////////////////////////////////////
// Win BRAM
////////////////////////////////////////////////////////////

win_bram u_win_bram
(
    .clka(clk),

    .ena(1'b1),

    .addra(win_mem_addr),

    .douta(win_data)
);

////////////////////////////////////////////////////////////
// Reservoir Weight BRAM
////////////////////////////////////////////////////////////

w_bram u_w_bram
(
    .clka(clk),
    .ena(1'b1),
    .addra(w_mem_addr),
    .douta(w_data)
);

////////////////////////////////////////////////////////////
// Input BRAM
////////////////////////////////////////////////////////////
// Depth = 4, Width = DW (16 bits). Holds the input feature vector u.
// Single-port synchronous ROM, same 1-cycle READ_LATENCY contract as
// win_bram/w_bram/state_bram. u_addr is generated by esn_neuron.
// The generated input_bram wrapper does not expose an enable pin, so
// only .clka/.addra/.douta are connected here (no .ena()).
////////////////////////////////////////////////////////////

input_bram u_input_bram
(
    .clka(clk),
    .addra(u_addr),
    .douta(u_data)
);

////////////////////////////////////////////////////////////
// Bias BRAM
////////////////////////////////////////////////////////////
// Depth = N_RES, Width = DW (16 bits). Holds the per-neuron bias
// term b_i, addressed directly by neuron_idx (neuron i reads
// bias[i] -- one scalar per neuron). Same 1-cycle READ_LATENCY
// contract as the other BRAMs.
////////////////////////////////////////////////////////////

bias_bram u_bias_bram
(
    .clka (clk),
    .ena  (1'b1),
    .addra(neuron_idx),
    .douta(bias)
);

////////////////////////////////////////////////////////////
// State Buffer Select (Ping-Pong Swap)
////////////////////////////////////////////////////////////
// buf_sel identifies which physical state_bram currently holds the
// OLD state vector x(k) (read-only for this pass) versus the NEW
// state vector x(k+1) (write-only for this pass).
//
//   buf_sel == 0 : state_bram_0 = OLD (read),  state_bram_1 = NEW (write)
//   buf_sel == 1 : state_bram_1 = OLD (read),  state_bram_0 = NEW (write)
//
// It must toggle EXACTLY ONCE per full reservoir pass. The controller's
// `done` output is a LEVEL (high for as long as the controller sits in
// FINISHED, which persists for as long as the external `start` input
// stays asserted -- see reservoir_controller.v). Toggling directly off
// that level would flip buf_sel once per cycle `done` is held, not
// once per pass (Rev 0.10 bugfix). Instead, edge-detect `done` locally
// so the swap is triggered by a genuine single-cycle pulse regardless
// of how long start/done happen to be held upstream. The swap itself
// is "free": no data is copied, only the role of each buffer flips.
////////////////////////////////////////////////////////////

reg buf_sel;
reg done_d1;
wire wea0_debug = store_en & buf_sel;
wire wea1_debug = store_en & ~buf_sel;

always @(posedge clk or negedge rst_n)
begin
    if(!rst_n)
        done_d1 <= 1'b0;
    else
        done_d1 <= done;
end

wire done_pulse = done & ~done_d1;

always @(posedge clk or negedge rst_n)
begin
    if(!rst_n)
        buf_sel <= 1'b0;
    else if(done_pulse)
        buf_sel <= ~buf_sel;
end

////////////////////////////////////////////////////////////
// State BRAM (Ping-Pong, Simple Dual-Port x2)
////////////////////////////////////////////////////////////
// Each buffer's read port (enb) is gated by buf_sel so only the
// buffer holding the current OLD state is actually read each cycle;
// the other buffer's read port is disabled. x_data is muxed from
// whichever buffer is OLD this pass, selected by buf_sel below. Only
// one buffer's write port is active at a time (store_en gated by
// buf_sel/~buf_sel), so a neuron's write-back this pass can never
// land in the buffer the reservoir is reading from this same pass.
//
// Verified self-consistent against the buf_sel==0/1 convention above
// for both values of buf_sel: the buffer being read is always the
// buffer NOT being written, in both states.
////////////////////////////////////////////////////////////

wire signed [DW-1:0] x_data_0;
wire signed [DW-1:0] x_data_1;

state_bram u_state_bram_0
(
    // Write port -- active only when buffer 0 is this pass's NEW buffer
    .clka(clk),
    .ena(1'b1),
    .wea({store_en & buf_sel}),
    .addra(neuron_idx),
    .dina(x_next),

    // Read port -- only enabled when buffer 0 is this pass's OLD buffer
    .clkb(clk),
    .enb(~buf_sel),
    .addrb(x_addr),
    .doutb(x_data_0)
);

state_bram u_state_bram_1
(
    // Write port -- active only when buffer 1 is this pass's NEW buffer
    .clka(clk),
    .ena(1'b1),
    .wea({store_en & ~buf_sel}),
    .addra(neuron_idx),
    .dina(x_next),

    // Read port -- only enabled when buffer 1 is this pass's OLD buffer
    .clkb(clk),
    .enb(buf_sel),
    .addrb(x_addr),
    .doutb(x_data_1)
);

// x_data always reflects whichever buffer holds the OLD state this pass
assign x_data = buf_sel ? x_data_1 : x_data_0;

////////////////////////////////////////////////////////////
// ESN Neuron
////////////////////////////////////////////////////////////
// TIMING CONTRACT: win_bram, w_bram, input_bram, and state_bram all
// have a synchronous READ_LATENCY of 1 cycle:
//     cycle N   : {win,w,u,x}_addr driven
//     cycle N+1 : {win,w,u,x}_data valid
// Verified: esn_neuron's S_WIN_READ / S_W_READ states correctly insert
// exactly one bubble cycle between driving each address and consuming
// the corresponding data (win_addr/u_addr in S_WIN_ADDR -> consumed in
// S_WIN_MAC; w_addr/x_addr in S_W_ADDR -> consumed in S_W_MAC), so no
// address is ever read one cycle too early.
//
// Rev 0.11: neuron_idx and buf_sel connected below purely for
// esn_neuron's internal debug $display (see esn_neuron.v Rev
// 0.08/0.09) -- both signals already existed in this module for
// other purposes and are simply fanned out to this instance as well.
////////////////////////////////////////////////////////////

esn_neuron
#(
    .DW(DW),
    .N_IN(N_IN),
    .N_RES(N_RES)
)
u_neuron
(
    .clk(clk),
    .rst_n(rst_n),

    .start(neuron_start),
    .done(neuron_done),

    .neuron_idx(neuron_idx),
    .buf_sel(buf_sel),

    .win_addr(win_addr),
    .win_data(win_data),

    .u_addr(u_addr),
    .u_data(u_data),

    .w_addr(w_addr),
    .w_data(w_data),

    .x_addr(x_addr),
    .x_data(x_data),

    .bias(bias),

    .x_next(x_next),

    .overflow(overflow)
);

endmodule
