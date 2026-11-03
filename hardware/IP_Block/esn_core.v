`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////
// esn_core.v -- reusable Echo State Network reservoir core (Rev 1.0)
//
//   x(t+1) = tanh( Win*u(t) + W*x(t) + b ),  Q6.10 fixed point, one neuron at
//   a time through ONE shared MAC (same datapath as the verified esn_top
//   Rev 0.12: esn_neuron, mac_accum_q6_10, tanh_lut, reservoir_controller and
//   address_generator are used UNCHANGED).
//
// What is new compared with esn_top
//   * No vendor IP: all memories are esn_ram (portable, inferred).
//   * Run-time loading: weights, bias and the input sequence are written
//     through the load port (ld_*), so one bitstream serves any trained ESN
//     of up to N_IN inputs / N_RES neurons -- no re-synthesis for new weights.
//   * clear: zeroes both state buffers, buf_sel and timestep (fresh run).
//   * timestep / busy are exposed for the host or bus wrapper.
//
// Load port (only while busy = 0)
//   ld_sel : 0 = Win   (depth N_IN*N_RES, row-major: neuron*N_IN + input)
//            1 = W     (depth N_RES*N_RES, row-major: neuron*N_RES + source)
//            2 = input (depth N_IN*T_MAX,  timestep*N_IN + input)
//            3 = bias  (depth N_RES)
//   ld_addr, ld_data (Q6.10 two's complement), ld_we (1-cycle strobe)
//
// Control
//   start : 1-cycle pulse, computes x(t+1) for the current timestep, then
//           timestep advances (wraps at T_MAX); done is high when finished.
//   clear : 1-cycle pulse (while idle), takes N_RES+1 cycles; busy = 1 meanwhile.
//
// Parameters N_IN >= 2, N_RES >= 2.
//////////////////////////////////////////////////////////////////////////////
module esn_core #(
    parameter DW        = 16,
    parameter N_IN      = 4,
    parameter N_RES     = 100,
    parameter T_MAX     = 64,
    parameter READ_LAT  = 2,
    parameter WIN_FILE  = "",
    parameter W_FILE    = "",
    parameter BIAS_FILE = "",
    parameter IN_FILE   = "",
    // widest load address (do not override)
    parameter AW_LD     = (($clog2(N_RES*N_RES) > $clog2(N_IN*T_MAX)) ?
                           (($clog2(N_RES*N_RES) > $clog2(N_IN*N_RES)) ? $clog2(N_RES*N_RES) : $clog2(N_IN*N_RES)) :
                           (($clog2(N_IN*T_MAX) > $clog2(N_IN*N_RES)) ? $clog2(N_IN*T_MAX) : $clog2(N_IN*N_RES)))
)(
    input  wire                       clk,
    input  wire                       rst_n,
    input  wire                       start,
    input  wire                       clear,
    output wire                       done,
    output wire                       busy,
    output wire [$clog2(T_MAX)-1:0]   timestep_o,

    // run-time memory load
    input  wire [1:0]                 ld_sel,
    input  wire [AW_LD-1:0]           ld_addr,
    input  wire signed [DW-1:0]       ld_data,
    input  wire                       ld_we,

    // observable state stream
    output wire signed [DW-1:0]       x_out,
    output wire                       x_valid,
    output wire                       ovf_out
);

localparam T_WIDTH = (T_MAX > 1) ? $clog2(T_MAX) : 1;
localparam AW_WIN  = $clog2(N_IN*N_RES);
localparam AW_W    = $clog2(N_RES*N_RES);
localparam AW_IN   = $clog2(N_IN*T_MAX);
localparam AW_RES  = $clog2(N_RES);

////////////////////////////////////////////////////////////
// controller / neuron wiring (identical to esn_top Rev 0.12)
////////////////////////////////////////////////////////////
wire neuron_start, neuron_done, reservoir_busy, store_en;
wire [AW_RES-1:0] neuron_idx;
wire signed [DW-1:0] x_next;
wire overflow;

reg [T_WIDTH-1:0] timestep;
assign timestep_o = timestep;

wire [$clog2(N_IN)-1:0]       win_addr;
wire [$clog2(N_IN)-1:0]       u_neuron_idx;
wire [AW_IN-1:0]              u_addr = (timestep * N_IN) + u_neuron_idx;
wire [AW_RES-1:0]             w_addr;
wire [AW_RES-1:0]             x_addr;

wire signed [DW-1:0] win_data, u_data, w_data, x_data, bias;

wire [AW_WIN-1:0] win_base_addr;
wire [AW_W-1:0]   w_base_addr;
wire [AW_WIN-1:0] win_mem_addr = win_base_addr + win_addr;
wire [AW_W-1:0]   w_mem_addr   = w_base_addr + w_addr;

reservoir_controller #(.N_RES(N_RES)) u_controller (
    .clk(clk), .rst_n(rst_n), .start(start), .done(done),
    .reservoir_busy(reservoir_busy),
    .neuron_start(neuron_start), .neuron_done(neuron_done),
    .neuron_idx(neuron_idx), .store_en(store_en));

address_generator #(.N_IN(N_IN), .N_RES(N_RES)) u_addr_gen (
    .neuron_idx(neuron_idx),
    .win_base_addr(win_base_addr), .w_base_addr(w_base_addr));

////////////////////////////////////////////////////////////
// weight / input / bias memories (run-time loadable)
////////////////////////////////////////////////////////////
esn_ram #(.DEPTH(N_IN*N_RES), .WIDTH(DW), .READ_LAT(READ_LAT), .INIT_FILE(WIN_FILE)) u_win_ram (
    .clk(clk), .we(ld_we & (ld_sel == 2'd0)), .waddr(ld_addr[AW_WIN-1:0]), .wdata(ld_data),
    .re(1'b1), .raddr(win_mem_addr), .rdata(win_data));

esn_ram #(.DEPTH(N_RES*N_RES), .WIDTH(DW), .READ_LAT(READ_LAT), .INIT_FILE(W_FILE)) u_w_ram (
    .clk(clk), .we(ld_we & (ld_sel == 2'd1)), .waddr(ld_addr[AW_W-1:0]), .wdata(ld_data),
    .re(1'b1), .raddr(w_mem_addr), .rdata(w_data));

esn_ram #(.DEPTH(N_IN*T_MAX), .WIDTH(DW), .READ_LAT(READ_LAT), .INIT_FILE(IN_FILE)) u_in_ram (
    .clk(clk), .we(ld_we & (ld_sel == 2'd2)), .waddr(ld_addr[AW_IN-1:0]), .wdata(ld_data),
    .re(1'b1), .raddr(u_addr), .rdata(u_data));

esn_ram #(.DEPTH(N_RES), .WIDTH(DW), .READ_LAT(READ_LAT), .INIT_FILE(BIAS_FILE)) u_bias_ram (
    .clk(clk), .we(ld_we & (ld_sel == 2'd3)), .waddr(ld_addr[AW_RES-1:0]), .wdata(ld_data),
    .re(1'b1), .raddr(neuron_idx), .rdata(bias));

////////////////////////////////////////////////////////////
// ping-pong select, timestep, clear sequencer
////////////////////////////////////////////////////////////
reg buf_sel;
reg done_d1;
always @(posedge clk or negedge rst_n)
    if (!rst_n) done_d1 <= 1'b0; else done_d1 <= done;
wire done_pulse = done & ~done_d1;

reg                clr_active;
reg [AW_RES-1:0]   clr_cnt;
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        clr_active <= 1'b0;
        clr_cnt    <= {AW_RES{1'b0}};
    end else if (clear && !clr_active && !reservoir_busy) begin
        clr_active <= 1'b1;
        clr_cnt    <= {AW_RES{1'b0}};
    end else if (clr_active) begin
        if (clr_cnt == N_RES - 1) clr_active <= 1'b0;
        else                      clr_cnt <= clr_cnt + 1'b1;
    end
end
wire clr_last = clr_active && (clr_cnt == N_RES - 1);

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) buf_sel <= 1'b0;
    else if (clr_last)   buf_sel <= 1'b0;
    else if (done_pulse) buf_sel <= ~buf_sel;
end

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) timestep <= {T_WIDTH{1'b0}};
    else if (clr_last) timestep <= {T_WIDTH{1'b0}};
    else if (done_pulse) begin
        if (timestep < T_MAX - 1) timestep <= timestep + 1'b1;
        else                      timestep <= {T_WIDTH{1'b0}};
    end
end

assign busy = reservoir_busy | clr_active;

////////////////////////////////////////////////////////////
// state memory: two buffers, write = new state, read = old state
////////////////////////////////////////////////////////////
wire signed [DW-1:0] x_data_0, x_data_1;

wire              we0   = (store_en & buf_sel)  | clr_active;
wire              we1   = (store_en & ~buf_sel) | clr_active;
wire [AW_RES-1:0] wadr  = clr_active ? clr_cnt : neuron_idx;
wire [DW-1:0]     wdat  = clr_active ? {DW{1'b0}} : x_next;

esn_ram #(.DEPTH(N_RES), .WIDTH(DW), .READ_LAT(READ_LAT)) u_state_ram_0 (
    .clk(clk), .we(we0), .waddr(wadr), .wdata(wdat),
    .re(~buf_sel), .raddr(x_addr), .rdata(x_data_0));

esn_ram #(.DEPTH(N_RES), .WIDTH(DW), .READ_LAT(READ_LAT)) u_state_ram_1 (
    .clk(clk), .we(we1), .waddr(wadr), .wdata(wdat),
    .re(buf_sel), .raddr(x_addr), .rdata(x_data_1));

assign x_data = buf_sel ? x_data_1 : x_data_0;

////////////////////////////////////////////////////////////
// neuron (unchanged)
////////////////////////////////////////////////////////////
esn_neuron #(.DW(DW), .N_IN(N_IN), .N_RES(N_RES)) u_neuron (
    .clk(clk), .rst_n(rst_n),
    .start(neuron_start), .done(neuron_done),
    .neuron_idx(neuron_idx), .buf_sel(buf_sel),
    .timestep({{(16-T_WIDTH){1'b0}}, timestep}),
    .win_addr(win_addr), .win_data(win_data),
    .u_addr(u_neuron_idx), .u_data(u_data),
    .w_addr(w_addr), .w_data(w_data),
    .x_addr(x_addr), .x_data(x_data),
    .bias(bias), .x_next(x_next), .overflow(overflow));

assign x_out   = x_next;
assign x_valid = store_en;
assign ovf_out = overflow;

endmodule
