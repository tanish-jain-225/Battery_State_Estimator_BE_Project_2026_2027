`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////
// esn_core_fast.v -- faster ESN reservoir core, drop-in for esn_core (Rev 1.0)
//
//   x(t+1) = tanh( Win*u(t) + W*x(t) + b ),  Q6.10, bit-exact with esn_core.
//
// Same ports, load map and arithmetic as esn_core. Three changes to the
// schedule, none to the arithmetic:
//   1. One MAC term per clock (pipelined) instead of one per four clocks.
//   2. Zero recurrent weights are skipped: after a weight load, a one-time
//      compression pass stores each neuron's nonzero W entries (value, column)
//      in an ELL list of K slots, padded with zero values.
//   3. P lanes compute P neurons at once, each with its own copy of the
//      previous state, so every lane can read its own column.
// The MAC (mac_accum_q6_10, 40-bit exact integer sum, rounding only at the
// end) and tanh_lut are the verified modules, used unchanged. Integer sums do
// not depend on order and zero products add nothing, so the result equals
// esn_core word for word.
//
// Cycles per update (no pending compression):
//   ceil(N_RES/P)*(N_IN+K) + 2*READ_LAT + P + 13 (see the testbench report)
// The first start after any Win/W/bias write also runs the compression pass
// (about N_RES*(N_IN+N_RES+K) cycles, once).
//
// Restrictions: K >= the largest number of nonzeros in any row of W (if a
// row has more, the extra entries are dropped and dense_err is set);
// N_IN + K >= P and N_IN + K >= 2*READ_LAT + 4.
//////////////////////////////////////////////////////////////////////////////
module esn_core_fast #(
    parameter DW        = 16,
    parameter N_IN      = 4,
    parameter N_RES     = 100,
    parameter T_MAX     = 64,
    parameter READ_LAT  = 2,
    parameter P         = 1,          // parallel lanes
    parameter K         = N_RES,      // ELL slots per neuron (max nonzeros per row)
    parameter WIN_FILE  = "",
    parameter W_FILE    = "",
    parameter BIAS_FILE = "",
    parameter IN_FILE   = "",
    parameter AW_LD     = (($clog2(N_RES*N_RES) > $clog2(N_IN*T_MAX)) ?
                           (($clog2(N_RES*N_RES) > $clog2(N_IN*N_RES)) ? $clog2(N_RES*N_RES) : $clog2(N_IN*N_RES)) :
                           (($clog2(N_IN*T_MAX) > $clog2(N_IN*N_RES)) ? $clog2(N_IN*T_MAX) : $clog2(N_IN*N_RES)))
)(
    input  wire                       clk,
    input  wire                       rst_n,
    input  wire                       start,
    input  wire                       clear,
    output reg                        done,
    output wire                       busy,
    output wire [$clog2(T_MAX)-1:0]   timestep_o,
    input  wire [1:0]                 ld_sel,
    input  wire [AW_LD-1:0]           ld_addr,
    input  wire signed [DW-1:0]       ld_data,
    input  wire                       ld_we,
    output reg  signed [DW-1:0]       x_out,
    output reg                        x_valid,
    output reg                        ovf_out,
    output reg                        dense_err     // sticky: a row of W had more than K nonzeros
);

localparam L       = READ_LAT;
localparam T_WIDTH = (T_MAX > 1) ? $clog2(T_MAX) : 1;
localparam AW_WIN  = $clog2(N_IN*N_RES);
localparam AW_W    = $clog2(N_RES*N_RES);
localparam AW_IN   = $clog2(N_IN*T_MAX);
localparam AW_RES  = (N_RES > 1) ? $clog2(N_RES) : 1;
localparam G       = (N_RES + P - 1) / P;           // neuron groups
localparam TT      = N_IN + K;                      // terms per neuron
localparam AW_E    = $clog2(G*TT);
localparam AW_G    = (G > 1) ? $clog2(G) : 1;
localparam AW_TT   = $clog2(TT + 1);
localparam AW_K    = $clog2(K + 1);
localparam AW_P    = (P > 1) ? $clog2(P) : 1;
localparam EW      = DW + AW_RES;                   // ELL entry: {column, value}

// -------------------------------------------------------------------------
// dense memories, written through the load port exactly as in esn_core
// -------------------------------------------------------------------------
reg  [AW_WIN-1:0] win_raddr;  wire signed [DW-1:0] win_rdata;
reg  [AW_W-1:0]   w_raddr;    wire signed [DW-1:0] w_rdata;
reg  [AW_RES-1:0] b_raddr;    wire signed [DW-1:0] b_rdata;
wire [AW_IN-1:0]  u_raddr;    wire signed [DW-1:0] u_rdata;

esn_ram #(.DEPTH(N_IN*N_RES), .WIDTH(DW), .READ_LAT(L), .INIT_FILE(WIN_FILE)) u_win_ram (
    .clk(clk), .we(ld_we & (ld_sel == 2'd0)), .waddr(ld_addr[AW_WIN-1:0]), .wdata(ld_data),
    .re(1'b1), .raddr(win_raddr), .rdata(win_rdata));
esn_ram #(.DEPTH(N_RES*N_RES), .WIDTH(DW), .READ_LAT(L), .INIT_FILE(W_FILE)) u_w_ram (
    .clk(clk), .we(ld_we & (ld_sel == 2'd1)), .waddr(ld_addr[AW_W-1:0]), .wdata(ld_data),
    .re(1'b1), .raddr(w_raddr), .rdata(w_rdata));
esn_ram #(.DEPTH(N_IN*T_MAX), .WIDTH(DW), .READ_LAT(L), .INIT_FILE(IN_FILE)) u_in_ram (
    .clk(clk), .we(ld_we & (ld_sel == 2'd2)), .waddr(ld_addr[AW_IN-1:0]), .wdata(ld_data),
    .re(1'b1), .raddr(u_raddr), .rdata(u_rdata));
esn_ram #(.DEPTH(N_RES), .WIDTH(DW), .READ_LAT(L), .INIT_FILE(BIAS_FILE)) u_bias_ram (
    .clk(clk), .we(ld_we & (ld_sel == 2'd3)), .waddr(ld_addr[AW_RES-1:0]), .wdata(ld_data),
    .re(1'b1), .raddr(b_raddr), .rdata(b_rdata));

reg dirty;   // weights changed since the last compression pass

// -------------------------------------------------------------------------
// top-level FSM
// -------------------------------------------------------------------------
localparam S_IDLE = 3'd0, S_CMP = 3'd1, S_RUN = 3'd2, S_DRAIN = 3'd3, S_CLR = 3'd4;
reg [2:0] st;
reg [T_WIDTH-1:0] timestep;
reg buf_sel;
assign timestep_o = timestep;
assign busy = (st != S_IDLE);

// ---------------------------- compression pass ---------------------------
// For each neuron i: read Win[i][0..N_IN-1] and W[i][0..N_RES-1] (one read per
// cycle), write Win to ELL slots 0..N_IN-1, nonzero W to slots N_IN+cnt, then
// pad the remaining slots with zero; copy bias[i] to the lane's bias bank.
localparam C_READ = 2'd0, C_WAIT = 2'd1, C_PAD = 2'd2, C_NEXT = 2'd3;
reg [1:0]         cst;
reg [AW_RES-1:0]  c_i;                  // neuron
reg [AW_P-1:0]    c_p;                  // its lane
reg [AW_G-1:0]    c_g;                  // its group (local row)
reg [AW_E-1:0]    c_ebase;              // c_g * TT
reg [AW_WIN-1:0]  c_winbase;            // c_i * N_IN
reg [AW_W-1:0]    c_wbase;              // c_i * N_RES
reg [$clog2(N_IN+N_RES+1)-1:0] c_q;    // read index
reg [AW_K-1:0]    c_cnt;                // nonzeros stored so far
reg [AW_K:0]      c_pad;                // next slot to pad (relative to N_IN)
reg [L+1:0]       c_wait;
wire cmp_finish = (st == S_CMP) && (cst == C_NEXT) && (c_i == N_RES - 1);
always @(posedge clk or negedge rst_n)
    if (!rst_n) dirty <= 1'b1;
    else if (ld_we && (ld_sel != 2'd2)) dirty <= 1'b1;
    else if (cmp_finish) dirty <= 1'b0;

// read-side tag pipeline (L stages): {valid, is_win, index}
reg                 cv  [0:L];
reg                 cwin[0:L];
reg [AW_RES-1:0]    cidx[0:L];
integer z;

// ELL / bias bank write port (shared by all lanes, enable per lane)
reg               e_we;
reg [AW_P-1:0]    e_lane;
reg [AW_E-1:0]    e_waddr;
reg [EW-1:0]      e_wdata;
reg               bb_we;
reg [AW_G-1:0]    bb_waddr;
reg signed [DW-1:0] bb_wdata;

// ------------------------------ compute pass -----------------------------
reg [AW_G-1:0]  r_g;          // group being issued
reg [AW_TT-1:0] r_k;          // term being issued
reg [AW_E-1:0]  r_eaddr;      // r_g*TT + r_k
reg             r_issue;      // a term is issued this cycle
reg [AW_E-1:0]  e_raddr;
reg [AW_G-1:0]  bb_raddr;

// issue tags, delayed to stage L and to stage 2L
reg            iv  [0:2*L];
reg            ifst[0:2*L];
reg            ilst[0:2*L];
reg            iin [0:2*L];
reg [AW_G-1:0] igrp[0:2*L];

// shared input u: read at issue, valid at stage L, delayed to 2L
reg signed [DW-1:0] u_d [0:L];

// write-back and completion
reg               wb_active;
reg [AW_P:0]      wb_n;
reg [AW_G-1:0]    wb_g;
reg [AW_RES:0]    wb_i;
reg signed [DW-1:0] wb_sh [0:P-1];
reg [AW_G:0]      groups_done;
reg [3:0]         drain_cnt;
reg               clr_active;
reg [AW_RES-1:0]  clr_cnt;

// per-lane signals
wire signed [DW-1:0]   x_rd    [0:P-1];
wire [EW-1:0]          e_rd    [0:P-1];
wire signed [DW-1:0]   bb_rd   [0:P-1];
wire signed [15:0]     mac_res [0:P-1];
wire                   mac_ov  [0:P-1];
wire                   mac_rv  [0:P-1];
wire                   th_vo   [0:P-1];
wire signed [15:0]     th_out  [0:P-1];

// state write (all copies get the same writes)
wire              s_we0 = clr_active | (wb_active & (wb_i < N_RES) &  buf_sel);
wire              s_we1 = clr_active | (wb_active & (wb_i < N_RES) & ~buf_sel);
wire [AW_RES-1:0] s_wad = clr_active ? clr_cnt : wb_i[AW_RES-1:0];
wire [DW-1:0]     s_wdt = clr_active ? {DW{1'b0}} : wb_sh[0];

genvar gp;
generate for (gp = 0; gp < P; gp = gp + 1) begin : lane
    // ELL entries of this lane's neurons (i = g*P + gp)
    esn_ram #(.DEPTH(G*TT), .WIDTH(EW), .READ_LAT(L)) u_ell (
        .clk(clk), .we(e_we & (e_lane == gp)), .waddr(e_waddr), .wdata(e_wdata),
        .re(1'b1), .raddr(e_raddr), .rdata(e_rd[gp]));
    esn_ram_dist #(.DEPTH(G), .WIDTH(DW), .READ_LAT(L)) u_bias_bank (
        .clk(clk), .we(bb_we & (e_lane == gp)), .waddr(bb_waddr), .wdata(bb_wdata),
        .re(1'b1), .raddr(bb_raddr), .rdata(bb_rd[gp]));

    // private copy of both state buffers
    wire [AW_RES-1:0] col = e_rd[gp][EW-1:DW];
    wire signed [DW-1:0] xr0, xr1;
    esn_ram_dist #(.DEPTH(N_RES), .WIDTH(DW), .READ_LAT(L)) u_s0 (
        .clk(clk), .we(s_we0), .waddr(s_wad), .wdata(s_wdt), .re(1'b1), .raddr(col), .rdata(xr0));
    esn_ram_dist #(.DEPTH(N_RES), .WIDTH(DW), .READ_LAT(L)) u_s1 (
        .clk(clk), .we(s_we1), .waddr(s_wad), .wdata(s_wdt), .re(1'b1), .raddr(col), .rdata(xr1));
    assign x_rd[gp] = buf_sel ? xr1 : xr0;   // read the old buffer (written last update)

    // weight value delayed from stage L to stage 2L
    reg signed [DW-1:0] val_d [0:L];
    integer q;
    always @(posedge clk) begin
        val_d[0] <= e_rd[gp][DW-1:0];
        for (q = 1; q < L; q = q + 1) val_d[q] <= val_d[q-1];
    end
    wire signed [DW-1:0] val2 = val_d[L-1];
    wire signed [15:0] a = val2;
    wire signed [15:0] b = iin[2*L-1] ? u_d[L-1] : x_rd[gp];

    mac_accum_q6_10 u_mac (
        .clk(clk), .rst_n(rst_n),
        .clear(iv[2*L-1] & ifst[2*L-1]), .en(iv[2*L-1]), .last(iv[2*L-1] & ilst[2*L-1]),
        .a(a), .b(b),
        .result(mac_res[gp]), .overflow(mac_ov[gp]), .result_valid(mac_rv[gp]));

    // bias of the group, captured when its last term is at stage L
    reg signed [DW-1:0] bias_h;
    always @(posedge clk) if (iv[L-1] & ilst[L-1]) bias_h <= bb_rd[gp];

    // bias, clip, tanh (as in esn_neuron)
    wire signed [17:0] sum = {{2{mac_res[gp][15]}}, mac_res[gp]} + {{2{bias_h[15]}}, bias_h};
    reg signed [15:0] th_in;
    reg               th_vi;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin th_in <= 16'sd0; th_vi <= 1'b0; end
        else begin
            th_vi <= mac_rv[gp];
            if (mac_rv[gp])
                th_in <= (sum > 18'sd5120) ? 16'sd5120 : (sum < -18'sd5120) ? -16'sd5120 : sum[15:0];
        end
    end
    tanh_lut u_tanh (.clk(clk), .rst_n(rst_n), .valid_in(th_vi), .z_in(th_in),
                     .valid_out(th_vo[gp]), .tanh_out(th_out[gp]));
end endgenerate

// group of the result currently in post-processing (captured with the last term)
reg [AW_G-1:0] grp_h;
always @(posedge clk) if (iv[2*L-1] & ilst[2*L-1]) grp_h <= igrp[2*L-1];

reg ovf_any;
integer ln;
always @(*) begin
    ovf_any = 1'b0;
    for (ln = 0; ln < P; ln = ln + 1) ovf_any = ovf_any | (mac_rv[ln] & mac_ov[ln]);
end

// -------------------------------------------------------------------------
// sequential control
// -------------------------------------------------------------------------
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        st <= S_IDLE; cst <= C_READ; done <= 1'b0; timestep <= 0; buf_sel <= 1'b0;
        c_i <= 0; c_p <= 0; c_g <= 0; c_ebase <= 0; c_winbase <= 0; c_wbase <= 0; c_q <= 0; c_cnt <= 0; c_pad <= 0; c_wait <= 0;
        e_we <= 1'b0; e_lane <= 0; e_waddr <= 0; e_wdata <= 0; bb_we <= 1'b0; bb_waddr <= 0; bb_wdata <= 0;
        win_raddr <= 0; w_raddr <= 0; b_raddr <= 0;
        r_g <= 0; r_k <= 0; r_eaddr <= 0; r_issue <= 1'b0;
        wb_active <= 1'b0; wb_n <= 0; wb_g <= 0; wb_i <= 0; groups_done <= 0; drain_cnt <= 0;
        clr_active <= 1'b0; clr_cnt <= 0;
        x_out <= 0; x_valid <= 1'b0; ovf_out <= 1'b0; dense_err <= 1'b0;
        for (z = 0; z <= L; z = z + 1) begin cv[z] <= 1'b0; cwin[z] <= 1'b0; cidx[z] <= 0; u_d[z] <= 0; end
        for (z = 0; z <= 2*L; z = z + 1) begin iv[z] <= 1'b0; ifst[z] <= 1'b0; ilst[z] <= 1'b0; iin[z] <= 1'b0; igrp[z] <= 0; end
    end else begin
        done <= 1'b0; e_we <= 1'b0; bb_we <= 1'b0; x_valid <= 1'b0;
        ovf_out <= ovf_any;

        // ---------------- issue tag pipeline (always shifting) ----------------
        iv[0] <= r_issue; ifst[0] <= (r_k == 0); ilst[0] <= (r_k == TT - 1); iin[0] <= (r_k < N_IN); igrp[0] <= r_g;
        for (z = 1; z <= 2*L; z = z + 1) begin
            iv[z] <= iv[z-1]; ifst[z] <= ifst[z-1]; ilst[z] <= ilst[z-1]; iin[z] <= iin[z-1]; igrp[z] <= igrp[z-1];
        end
        // a term issued in cycle c has its tag at index s in cycle c+1+s; RAM data
        // addressed in cycle c arrives in cycle c+L (tag index L-1), x in c+2L (2L-1).
        u_d[0] <= u_rdata;
        for (z = 1; z <= L; z = z + 1) u_d[z] <= u_d[z-1];

        // compression read-tag pipeline
        for (z = 1; z <= L; z = z + 1) begin cv[z] <= cv[z-1]; cwin[z] <= cwin[z-1]; cidx[z] <= cidx[z-1]; end
        cv[0] <= 1'b0;

        // ---------------- write-back serializer ----------------
        if (wb_active) begin
            if (wb_i < N_RES) begin x_out <= wb_sh[0]; x_valid <= 1'b1; end
            for (z = 0; z < P - 1; z = z + 1) wb_sh[z] <= wb_sh[z+1];
            wb_i <= wb_i + 1'b1;
            if (wb_n == P - 1) begin wb_active <= 1'b0; groups_done <= groups_done + 1'b1; end
            else wb_n <= wb_n + 1'b1;
        end
        if (th_vo[0]) begin
            wb_active <= 1'b1; wb_n <= 0; wb_g <= grp_h; wb_i <= grp_h * P;
            for (z = 0; z < P; z = z + 1) wb_sh[z] <= th_out[z];
        end

        case (st)
        S_IDLE: begin
            r_issue <= 1'b0;
            if (clear) begin
                st <= S_CLR; clr_active <= 1'b1; clr_cnt <= 0;
            end else if (start) begin
                if (dirty) begin
                    st <= S_CMP; cst <= C_READ; dense_err <= 1'b0;
                    c_i <= 0; c_p <= 0; c_g <= 0; c_ebase <= 0; c_winbase <= 0; c_wbase <= 0;
                    c_q <= 0; c_cnt <= 0;
                end else begin
                    st <= S_RUN; r_g <= 0; r_k <= 0; r_eaddr <= 0; r_issue <= 1'b1; groups_done <= 0;
                end
            end
        end

        S_CLR: begin
            if (clr_cnt == N_RES - 1) begin
                clr_active <= 1'b0; st <= S_IDLE; buf_sel <= 1'b0; timestep <= 0;
            end else clr_cnt <= clr_cnt + 1'b1;
        end

        S_CMP: begin
            case (cst)
            C_READ: begin
                // issue one read: Win entries first, then W entries
                cv[0] <= 1'b1;
                if (c_q < N_IN) begin
                    win_raddr <= c_winbase + c_q; cwin[0] <= 1'b1; cidx[0] <= c_q;
                end else begin
                    w_raddr <= c_wbase + (c_q - N_IN); cwin[0] <= 1'b0; cidx[0] <= c_q - N_IN;
                end
                if (c_q == 0) b_raddr <= c_i;
                if (c_q == N_IN + N_RES - 1) begin cst <= C_WAIT; c_wait <= 0; end
                else c_q <= c_q + 1'b1;
            end
            C_WAIT: begin
                c_wait <= c_wait + 1'b1;
                if (c_wait == L + 1) begin cst <= C_PAD; c_pad <= c_cnt; end
            end
            C_PAD: begin
                if (c_pad < K) begin
                    e_we <= 1'b1; e_lane <= c_p; e_waddr <= c_ebase + N_IN + c_pad; e_wdata <= {EW{1'b0}};
                    c_pad <= c_pad + 1'b1;
                end else begin
                    bb_we <= 1'b1; bb_waddr <= c_g; bb_wdata <= b_rdata; e_lane <= c_p;
                    cst <= C_NEXT;
                end
            end
            C_NEXT: begin
                if (c_i == N_RES - 1) begin
                    // weights ready, run the update that was requested
                    st <= S_RUN; r_g <= 0; r_k <= 0; r_eaddr <= 0; r_issue <= 1'b1; groups_done <= 0;
                end else begin
                    c_i <= c_i + 1'b1; c_q <= 0; c_cnt <= 0; cst <= C_READ;
                    c_winbase <= c_winbase + N_IN; c_wbase <= c_wbase + N_RES;
                    if (c_p == P - 1) begin c_p <= 0; c_g <= c_g + 1'b1; c_ebase <= c_ebase + TT; end
                    else c_p <= c_p + 1'b1;
                end
            end
            endcase
        end

        S_RUN: begin
            // one term per cycle, all lanes share the address
            if (r_k == TT - 1) begin
                r_k <= 0;
                if (r_g == G - 1) begin r_issue <= 1'b0; st <= S_DRAIN; end
                else r_g <= r_g + 1'b1;
            end else r_k <= r_k + 1'b1;
            r_eaddr <= r_eaddr + 1'b1;
        end

        S_DRAIN: begin
            if (groups_done == G && !wb_active) begin
                drain_cnt <= drain_cnt + 1'b1;
                if (drain_cnt == 4'd5) begin
                    // let the readout finish its last sum before done
                    drain_cnt <= 0; done <= 1'b1; st <= S_IDLE; buf_sel <= ~buf_sel;
                    timestep <= (timestep == T_MAX - 1) ? {T_WIDTH{1'b0}} : timestep + 1'b1;
                end
            end
        end
        default: st <= S_IDLE;
        endcase

        // compression write side: data of the read issued L+1 cycles earlier
        if (st == S_CMP && cv[L]) begin
            if (cwin[L]) begin
                e_we <= 1'b1; e_lane <= c_p; e_waddr <= c_ebase + cidx[L]; e_wdata <= {{AW_RES{1'b0}}, win_rdata};
            end else if (w_rdata != 0) begin
                if (c_cnt < K) begin
                    e_we <= 1'b1; e_lane <= c_p; e_waddr <= c_ebase + N_IN + c_cnt;
                    e_wdata <= {cidx[L], w_rdata};
                    c_cnt <= c_cnt + 1'b1;
                end else dense_err <= 1'b1;
            end
        end
    end
end

// read addresses of the compute pass (combinational from the issue counters)
always @(*) begin
    e_raddr  = r_eaddr;
    bb_raddr = r_g;
end
// u address follows the issued term (only used for k < N_IN)
assign u_raddr = timestep * N_IN + r_k[$clog2(N_IN)-1:0];

endmodule
