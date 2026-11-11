`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////
// esn_axi_ip.v -- AXI4-Lite + AXI4-Stream Echo State Network accelerator (Rev 1.0)
//
//   esn_core (reservoir) + esn_readout (SOC per step, SOH per window)
//
//   s_axi_*   AXI4-Lite slave, 32-bit : control, status, memory load window
//   s_axis_*  AXI4-Stream slave       : one beat = one time step u(t), N_IN x int16 (Q6.10)
//   m_axis_*  AXI4-Stream master, 64b : one beat per step
//                [15:0]  SOC  (Q2.14)    [21:16] step index
//                [47:32] SOH  (Q2.14)    (meaningful when TLAST = 1, the last step of the window)
//   irq       level, OR of enabled IRQ_STATUS bits
//
// Register map (byte offsets, 32-bit registers)
//   0x00 ID        RO  0x45534E31 ("ESN1")
//   0x04 CAPS      RO  [7:0] N_IN  [19:8] N_RES  [31:20] T_MAX
//   0x08 CTRL      RW  [0] START (write 1, self-clearing)   [1] CLEAR (write 1, self-clearing)
//                      [2] STREAM_EN (level)
//   0x0C STATUS    RO  [0] busy   [1] stream FSM active   [2] overflow seen (sticky, cleared by CLEAR)
//                     [3] W row has more than K nonzeros (FAST build only; set at the first start after a load)
//   0x10 IRQ_STAT  RW1C [0] STEP_DONE  [1] SOH_DONE  [2] OVERFLOW
//   0x14 IRQ_EN    RW  same bits as IRQ_STAT
//   0x18 TIMESTEP  RO  index of the next time step
//   0x1C CYCLES    RO  clock cycles from start to done of the last step
//   0x20 SOC       RO  [15:0] SOC Q2.14   [21:16] step it belongs to
//   0x24 SOH       RO  [15:0] SOH Q2.14
//   0x28 MEM_SEL   RW  0 Win, 1 W, 2 input, 3 bias, 4 readout SOC weights, 5 readout SOH weights
//   0x2C MEM_ADDR  RW  [AW-1:0] address, [31] auto-increment after every MEM_DATA write
//   0x30 MEM_DATA  WO  write = store [17:0] (Q6.10 for 0..3, Q4.14 for 4..5) at MEM_SEL/MEM_ADDR
//
// Use: load memories (idle only) -> CTRL.CLEAR -> either CTRL.START once per step
//      (write the step's inputs to memory 2 first) or STREAM_EN=1 and feed s_axis.
//////////////////////////////////////////////////////////////////////////////
module esn_axi_ip #(
    parameter N_IN    = 4,
    parameter N_RES   = 100,
    parameter T_MAX   = 64,             // power of two (SOH is the mean over T_MAX steps)
    parameter READ_LAT = 2,
    parameter FAST    = 0,              // 1: esn_core_fast (pipelined, sparse W, P lanes), same results
    parameter P       = 1,              // lanes (FAST only)
    parameter K       = N_RES           // nonzeros per row of W (FAST only)
)(
    input  wire                     aclk,
    input  wire                     aresetn,

    // AXI4-Lite slave
    input  wire [7:0]               s_axi_awaddr,
    input  wire                     s_axi_awvalid,
    output wire                     s_axi_awready,
    input  wire [31:0]              s_axi_wdata,
    input  wire [3:0]               s_axi_wstrb,
    input  wire                     s_axi_wvalid,
    output wire                     s_axi_wready,
    output wire [1:0]               s_axi_bresp,
    output reg                      s_axi_bvalid,
    input  wire                     s_axi_bready,
    input  wire [7:0]               s_axi_araddr,
    input  wire                     s_axi_arvalid,
    output wire                     s_axi_arready,
    output reg  [31:0]              s_axi_rdata,
    output wire [1:0]               s_axi_rresp,
    output reg                      s_axi_rvalid,
    input  wire                     s_axi_rready,

    // AXI4-Stream slave: input vector u(t)
    input  wire [N_IN*16-1:0]       s_axis_tdata,
    input  wire                     s_axis_tvalid,
    output wire                     s_axis_tready,

    // AXI4-Stream master: results
    output wire [63:0]              m_axis_tdata,
    output wire                     m_axis_tvalid,
    input  wire                     m_axis_tready,
    output wire                     m_axis_tlast,

    output wire                     irq
);

localparam AW_CORE = (($clog2(N_RES*N_RES) > $clog2(N_IN*T_MAX)) ?
                      (($clog2(N_RES*N_RES) > $clog2(N_IN*N_RES)) ? $clog2(N_RES*N_RES) : $clog2(N_IN*N_RES)) :
                      (($clog2(N_IN*T_MAX) > $clog2(N_IN*N_RES)) ? $clog2(N_IN*T_MAX) : $clog2(N_IN*N_RES)));
localparam IW      = $clog2(N_RES + 1);
localparam SW      = (T_MAX > 1) ? $clog2(T_MAX) : 1;
localparam AW_MAX  = (AW_CORE > IW) ? AW_CORE : IW;

wire clk   = aclk;
wire rst_n = aresetn;

assign s_axi_bresp = 2'b00;
assign s_axi_rresp = 2'b00;

////////////////////////////////////////////////////////////
// registers
////////////////////////////////////////////////////////////
reg        ctl_stream_en;
reg        reg_start, reg_clear;           // 1-cycle pulses
reg [2:0]  irq_stat, irq_en;
reg [3:0]  mem_sel;
reg [31:0] mem_addr;
reg        ld_we_r;                        // register-driven load strobe
reg [17:0] ld_data_r;
reg        ovf_seen;

reg [15:0] soc_r, soh_r;
reg [SW-1:0] step_r;
reg [31:0] cyc_cnt, cyc_last;
reg        running;

////////////////////////////////////////////////////////////
// AXI4-Lite write / read channels
////////////////////////////////////////////////////////////
wire wr_fire = s_axi_awvalid & s_axi_wvalid & ~s_axi_bvalid;
assign s_axi_awready = wr_fire;
assign s_axi_wready  = wr_fire;
wire [5:0] waddr = s_axi_awaddr[7:2];

wire rd_fire = s_axi_arvalid & ~s_axi_rvalid;
assign s_axi_arready = rd_fire;

wire core_busy, stream_busy;
wire [31:0] caps = (T_MAX << 20) | (N_RES << 8) | N_IN;
wire [SW-1:0] timestep;

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        s_axi_bvalid <= 1'b0;
        ctl_stream_en <= 1'b0;
        reg_start <= 1'b0; reg_clear <= 1'b0;
        irq_en <= 3'b000;
        mem_sel <= 4'd0; mem_addr <= 32'd0; ld_we_r <= 1'b0; ld_data_r <= 18'd0;
    end else begin
        reg_start <= 1'b0;
        reg_clear <= 1'b0;
        ld_we_r   <= 1'b0;
        if (s_axi_bvalid & s_axi_bready) s_axi_bvalid <= 1'b0;
        if (wr_fire) begin
            s_axi_bvalid <= 1'b1;
            case (waddr)
            6'h02: begin   // CTRL
                if (s_axi_wdata[0]) reg_start <= 1'b1;
                if (s_axi_wdata[1]) reg_clear <= 1'b1;
                ctl_stream_en <= s_axi_wdata[2];
            end
            6'h05: irq_en   <= s_axi_wdata[2:0];
            6'h0A: mem_sel  <= s_axi_wdata[3:0];
            6'h0B: mem_addr <= s_axi_wdata;
            6'h0C: begin   // MEM_DATA
                ld_data_r <= s_axi_wdata[17:0];
                ld_we_r   <= 1'b1;
                if (mem_addr[31]) mem_addr[30:0] <= mem_addr[30:0] + 1'b1;
            end
            default: ;
            endcase
        end
    end
end

////////////////////////////////////////////////////////////
// stream FSM
////////////////////////////////////////////////////////////
localparam ST_IDLE = 3'd0, ST_LOAD = 3'd1, ST_START = 3'd2, ST_RUN = 3'd3, ST_RD = 3'd4, ST_OUT = 3'd5;
reg [2:0]            st;
reg [N_IN*16-1:0]    sh;
reg [$clog2(N_IN+1)-1:0] li;
reg                  got_soc;
wire                 fsm_start = (st == ST_START);
wire                 done_w;
reg                  done_q;
always @(posedge clk or negedge rst_n) if (!rst_n) done_q <= 1'b0; else done_q <= done_w;
wire done_rise = done_w & ~done_q;

wire soc_valid, soh_valid; wire [SW-1:0] soc_step; wire signed [15:0] soc, soh;

assign stream_busy   = (st != ST_IDLE);
assign s_axis_tready = (st == ST_IDLE) & ctl_stream_en & ~core_busy & ~running & ~reg_start & ~reg_clear;
wire   s_fire        = s_axis_tvalid & s_axis_tready;

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        st <= ST_IDLE; sh <= {N_IN*16{1'b0}}; li <= 0; got_soc <= 1'b0;
    end else begin
        case (st)
        ST_IDLE: if (s_fire) begin sh <= s_axis_tdata; li <= 0; st <= ST_LOAD; end
        ST_LOAD: begin
            if (li == N_IN - 1) st <= ST_START; else li <= li + 1'b1;
        end
        ST_START: begin got_soc <= 1'b0; st <= ST_RUN; end
        ST_RUN:   if (done_rise) st <= ST_RD;
        ST_RD:    if (got_soc | soc_valid) st <= ST_OUT;
        ST_OUT:   if (m_axis_tready) st <= ST_IDLE;
        default:  st <= ST_IDLE;
        endcase
        if (soc_valid) got_soc <= 1'b1;
    end
end

////////////////////////////////////////////////////////////
// core load-port mux (register window vs stream loader)
////////////////////////////////////////////////////////////
// ld_addr_q captures MEM_ADDR at the MEM_DATA write (before auto-increment) so that the
// registered strobe ld_we_r, ld_data_r and ld_addr_q are aligned.
reg [31:0] ld_addr_q;
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) ld_addr_q <= 32'd0;
    else if (wr_fire && waddr == 6'h0C) ld_addr_q <= mem_addr;
end

wire fsm_load = (st == ST_LOAD);
wire [AW_CORE-1:0] core_ld_addr_str = (timestep * N_IN) + li;
wire               core_ld_we   = fsm_load | (ld_we_r & (mem_sel < 4'd4));
wire [1:0]         core_ld_sel  = fsm_load ? 2'd2 : mem_sel[1:0];
wire [AW_CORE-1:0] core_ld_addr = fsm_load ? core_ld_addr_str : ld_addr_q[AW_CORE-1:0];
wire signed [15:0] core_ld_data = fsm_load ? sh[li*16 +: 16] : ld_data_r[15:0];

// readout weight window: mem_sel 4 (SOC) or 5 (SOH)
wire rw_we  = ld_we_r & (mem_sel[3:1] == 3'd2);
wire rw_sel = mem_sel[0];

////////////////////////////////////////////////////////////
// start / clear into the core
////////////////////////////////////////////////////////////
wire start_core = (reg_start & ~core_busy & ~stream_busy) | fsm_start;
wire clear_core = reg_clear;

wire signed [15:0] x_out; wire x_valid, ovf_out, dense_err;

generate if (FAST) begin : g_fast
esn_core_fast #(.N_IN(N_IN), .N_RES(N_RES), .T_MAX(T_MAX), .READ_LAT(READ_LAT), .P(P), .K(K)) u_core (
    .clk(clk), .rst_n(rst_n), .start(start_core), .clear(clear_core), .done(done_w), .busy(core_busy),
    .timestep_o(timestep), .ld_sel(core_ld_sel), .ld_addr(core_ld_addr), .ld_data(core_ld_data), .ld_we(core_ld_we),
    .x_out(x_out), .x_valid(x_valid), .ovf_out(ovf_out), .dense_err(dense_err));
end else begin : g_ref
esn_core #(.N_IN(N_IN), .N_RES(N_RES), .T_MAX(T_MAX), .READ_LAT(READ_LAT)) u_core (
    .clk(clk), .rst_n(rst_n), .start(start_core), .clear(clear_core), .done(done_w), .busy(core_busy),
    .timestep_o(timestep), .ld_sel(core_ld_sel), .ld_addr(core_ld_addr), .ld_data(core_ld_data), .ld_we(core_ld_we),
    .x_out(x_out), .x_valid(x_valid), .ovf_out(ovf_out));
assign dense_err = 1'b0;
end endgenerate

esn_readout #(.N_RES(N_RES), .T_STEPS(T_MAX)) u_readout (
    .clk(clk), .rst_n(rst_n), .clear(clear_core), .x_in(x_out), .x_valid(x_valid),
    .rw_we(rw_we), .rw_sel(rw_sel), .rw_addr(ld_addr_q[IW-1:0]), .rw_data(ld_data_r),
    .soc(soc), .soc_valid(soc_valid), .soc_step(soc_step), .soh(soh), .soh_valid(soh_valid));

////////////////////////////////////////////////////////////
// status, results, IRQ, cycle counter
////////////////////////////////////////////////////////////
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        soc_r <= 16'd0; soh_r <= 16'd0; step_r <= {SW{1'b0}};
        irq_stat <= 3'b000; ovf_seen <= 1'b0;
        running <= 1'b0; cyc_cnt <= 32'd0; cyc_last <= 32'd0;
    end else begin
        if (soc_valid) begin soc_r <= soc; step_r <= soc_step; irq_stat[0] <= 1'b1; end
        if (soh_valid) begin soh_r <= soh; irq_stat[1] <= 1'b1; end
        if (ovf_out)   begin ovf_seen <= 1'b1; irq_stat[2] <= 1'b1; end
        if (reg_clear) ovf_seen <= 1'b0;
        if (wr_fire && waddr == 6'h04)             // IRQ_STAT write-1-to-clear (does not race a set)
            irq_stat <= (irq_stat & ~s_axi_wdata[2:0])
                        | {ovf_out, soh_valid, soc_valid};
        if (start_core) begin running <= 1'b1; cyc_cnt <= 32'd1; end
        else if (running) begin
            cyc_cnt <= cyc_cnt + 1'b1;
            if (done_rise) begin running <= 1'b0; cyc_last <= cyc_cnt; end
        end
    end
end

assign irq = |(irq_stat & irq_en);

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin s_axi_rvalid <= 1'b0; s_axi_rdata <= 32'd0; end
    else begin
        if (s_axi_rvalid & s_axi_rready) s_axi_rvalid <= 1'b0;
        if (rd_fire) begin
            s_axi_rvalid <= 1'b1;
            case (s_axi_araddr[7:2])
            6'h00: s_axi_rdata <= 32'h45534E31;
            6'h01: s_axi_rdata <= caps;
            6'h02: s_axi_rdata <= {29'd0, ctl_stream_en, 2'b00};
            6'h03: s_axi_rdata <= {28'd0, dense_err, ovf_seen, stream_busy, core_busy | stream_busy};
            6'h04: s_axi_rdata <= {29'd0, irq_stat};
            6'h05: s_axi_rdata <= {29'd0, irq_en};
            6'h06: s_axi_rdata <= {{(32-SW){1'b0}}, timestep};
            6'h07: s_axi_rdata <= cyc_last;
            6'h08: s_axi_rdata <= {10'd0, {(6-SW){1'b0}}, step_r, soc_r};
            6'h09: s_axi_rdata <= {16'd0, soh_r};
            6'h0A: s_axi_rdata <= {28'd0, mem_sel};
            6'h0B: s_axi_rdata <= mem_addr;
            default: s_axi_rdata <= 32'd0;
            endcase
        end
    end
end

////////////////////////////////////////////////////////////
// result stream
////////////////////////////////////////////////////////////
assign m_axis_tvalid = (st == ST_OUT);
assign m_axis_tdata  = {16'd0, soh_r, 10'd0, {(6-SW){1'b0}}, step_r, soc_r};
assign m_axis_tlast  = (step_r == T_MAX - 1);

endmodule
