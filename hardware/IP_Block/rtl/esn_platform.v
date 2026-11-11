`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////
// esn_platform.v -- new-data estimation platform: ESN + EKF + UKF on one FPGA (Rev 1.0)
//
// A host (laptop) talks to this module over UART with framed commands. For every
// time step the host sends ONE measurement frame and the FPGA runs all three
// estimators at the same time on that sample and returns their SOC estimates
// (plus the ESN SOH at the end of a 64-step window) and the measured cycle counts.
//
// Frame (both directions):  0xA5 | cmd | len_lo | len_hi | payload[len] | chk
//   chk = (cmd + len_lo + len_hi + sum(payload)) mod 256
//
// Host -> FPGA
//   0x01 WRITE  payload: target, wb, addr_lo, addr_hi, then words (wb bytes each, little endian)
//        target 0 ESN Win   1 ESN W   2 ESN input   3 ESN bias            (Q6.10, wb = 2)
//               4 readout SOC weights   5 readout SOH weights (index 0..N_RES, N_RES = offset)  (Q4.14, wb = 4)
//               8 EKF registers  9 UKF registers  (word address = register index, wb = 4)
//                 EKF 32 = RE (ESN measurement variance, Q2.30), 33 = FUSE (nonzero: EKF also uses the ESN SOC)
//              10 EKF OCV  11 EKF slope  12 UKF OCV  13 UKF slope  (1024 entries, wb = 4)
//        address auto-increments per word. Reply 0x81 [status].
//   0x02 CTRL   payload: flags  bit0 = clear ESN state / timestep / readout, bit1 = EKF init pulse
//        Reply 0x81 [status] (after the ESN clear finished).
//   0x03 STEP   payload: u[0..N_IN-1] int16 (Q6.10) | I int32 (Q4.28) | Vmeas int32 (Q4.28)
//        Runs ESN + EKF + UKF concurrently. Reply 0x83 (21 bytes):
//          [0] step index  [1] flags (bit0 = SOH valid, bit1 = ESN MAC overflow seen)
//          [2:3] ESN SOC Q2.14   [4:7] EKF SOC Q2.30   [8:11] UKF SOC Q2.30   [12:13] ESN SOH Q2.14
//          [14:16] ESN cycles    [17:18] EKF cycles    [19:20] UKF cycles
//   0x04 PING   Reply 0x84: 'E','P', 1, N_IN, N_RES lo/hi, T_MAX lo/hi
// Reply status: 0 = ok, 1 = bad checksum, 2 = unknown command.
//
// A WRITE frame with a bad checksum may already have written part of its data;
// the host must resend it (the reply tells it so).
//////////////////////////////////////////////////////////////////////////////
module esn_platform #(
    parameter N_IN         = 4,
    parameter N_RES        = 100,
    parameter T_MAX        = 64,
    parameter CLKS_PER_BIT = 694,           // f_clk / baud (80 MHz / 115200)
    parameter TIMEOUT      = 4000000,       // parser watchdog in clocks (50 ms at 80 MHz)
    parameter FAST         = 0,             // 1: esn_core_fast, same results, fewer cycles
    parameter P            = 1,
    parameter K            = N_RES
)(
    input  wire clk,
    input  wire rst_n,
    input  wire uart_rx_i,
    output wire uart_tx_o,
    output wire busy_o,            // a STEP / CTRL is executing
    output wire frame_ok_o,        // pulse: a frame with good checksum was received
    output wire ovf_seen_o
);

localparam SW      = (T_MAX > 1) ? $clog2(T_MAX) : 1;
localparam AW_LD   = (($clog2(N_RES*N_RES) > $clog2(N_IN*T_MAX)) ?
                      (($clog2(N_RES*N_RES) > $clog2(N_IN*N_RES)) ? $clog2(N_RES*N_RES) : $clog2(N_IN*N_RES)) :
                      (($clog2(N_IN*T_MAX) > $clog2(N_IN*N_RES)) ? $clog2(N_IN*T_MAX) : $clog2(N_IN*N_RES)));
localparam IW      = $clog2(N_RES + 1);
localparam PL_BYTES = 2*N_IN + 8;

wire [7:0]  n_in_w  = N_IN;
wire [15:0] n_res_w = N_RES;
wire [15:0] t_max_w = T_MAX;
localparam CMD_WRITE = 8'h01, CMD_CTRL = 8'h02, CMD_STEP = 8'h03, CMD_PING = 8'h04;

////////////////////////////////////////////////////////////
// UART
////////////////////////////////////////////////////////////
wire       rx_valid; wire [7:0] rx_data;
reg        tx_send; reg [7:0] tx_data; wire tx_busy;
uart_rx #(.CLKS_PER_BIT(CLKS_PER_BIT)) u_rx (.clk(clk), .rst_n(rst_n), .rx(uart_rx_i), .valid(rx_valid), .data(rx_data));
uart_tx #(.CLKS_PER_BIT(CLKS_PER_BIT)) u_tx (.clk(clk), .rst_n(rst_n), .send(tx_send), .data(tx_data), .tx(uart_tx_o), .busy(tx_busy));

////////////////////////////////////////////////////////////
// estimators
////////////////////////////////////////////////////////////
reg                  esn_start, esn_clear;
reg  [1:0]           esn_ld_sel;
reg  [AW_LD-1:0]     esn_ld_addr;
reg  signed [15:0]   esn_ld_data;
reg                  esn_ld_we;
wire                 esn_done, esn_busy, ovf_out, x_valid, dense_err;
wire [SW-1:0]        timestep;
wire signed [15:0]   x_out;

generate if (FAST) begin : g_fast
esn_core_fast #(.N_IN(N_IN), .N_RES(N_RES), .T_MAX(T_MAX), .READ_LAT(2), .P(P), .K(K)) u_esn (
    .clk(clk), .rst_n(rst_n), .start(esn_start), .clear(esn_clear), .done(esn_done), .busy(esn_busy),
    .timestep_o(timestep), .ld_sel(esn_ld_sel), .ld_addr(esn_ld_addr), .ld_data(esn_ld_data), .ld_we(esn_ld_we),
    .x_out(x_out), .x_valid(x_valid), .ovf_out(ovf_out), .dense_err(dense_err));
end else begin : g_ref
esn_core #(.N_IN(N_IN), .N_RES(N_RES), .T_MAX(T_MAX), .READ_LAT(2)) u_esn (
    .clk(clk), .rst_n(rst_n), .start(esn_start), .clear(esn_clear), .done(esn_done), .busy(esn_busy),
    .timestep_o(timestep), .ld_sel(esn_ld_sel), .ld_addr(esn_ld_addr), .ld_data(esn_ld_data), .ld_we(esn_ld_we),
    .x_out(x_out), .x_valid(x_valid), .ovf_out(ovf_out));
assign dense_err = 1'b0;
end endgenerate

reg                  rw_we, rw_sel;
reg  [IW-1:0]        rw_addr;
reg  signed [17:0]   rw_data;
wire signed [15:0]   soc, soh; wire soc_valid, soh_valid; wire [SW-1:0] soc_step;
esn_readout #(.N_RES(N_RES), .T_STEPS(T_MAX)) u_ro (
    .clk(clk), .rst_n(rst_n), .clear(esn_clear), .x_in(x_out), .x_valid(x_valid),
    .rw_we(rw_we), .rw_sel(rw_sel), .rw_addr(rw_addr), .rw_data(rw_data),
    .soc(soc), .soc_valid(soc_valid), .soc_step(soc_step), .soh(soh), .soh_valid(soh_valid));

// result latches (declared here because the EKF reads the ESN SOC for fusion)
reg        esn_seen, ekf_seen, ukf_seen, soc_seen, soh_seen, ovf_seen;
reg signed [15:0] soc_l, soh_l; reg [SW-1:0] step_l;
reg                  ekf_cfg_we, ekf_init, ekf_start, ekf_lut_we, ekf_lut_sel;
reg  [5:0]           ekf_cfg_addr;
reg  signed [31:0]   cfg_data;
reg  [9:0]           lut_waddr;
reg  signed [31:0]   lut_wdata;
wire                 ekf_done, ekf_busy; wire signed [31:0] ekf_soc;
ekf_core #(.OCV_FILE(""), .SLOPE_FILE("")) u_ekf (
    .clk(clk), .rst_n(rst_n), .cfg_we(ekf_cfg_we), .cfg_addr(ekf_cfg_addr), .cfg_data(cfg_data),
    .init(ekf_init), .start(ekf_start), .done(ekf_done), .soc_out(ekf_soc), .busy(ekf_busy),
    .lut_we(ekf_lut_we), .lut_sel(ekf_lut_sel), .lut_waddr(lut_waddr), .lut_wdata(lut_wdata),
    .z_in(soc_l), .z_valid(soc_seen));      // ESN fusion: this step's ESN SOC (used only when EKF FUSE != 0)

reg                  ukf_cfg_we, ukf_start, ukf_lut_we, ukf_lut_sel;
reg  [5:0]           ukf_cfg_addr;
wire                 ukf_done, ukf_busy; wire signed [31:0] ukf_soc;
ukf_core #(.OCV_FILE(""), .SLOPE_FILE("")) u_ukf (
    .clk(clk), .rst_n(rst_n), .cfg_we(ukf_cfg_we), .cfg_addr(ukf_cfg_addr), .cfg_data(cfg_data),
    .start(ukf_start), .done(ukf_done), .soc_out(ukf_soc), .busy(ukf_busy),
    .lut_we(ukf_lut_we), .lut_sel(ukf_lut_sel), .lut_waddr(lut_waddr), .lut_wdata(lut_wdata));

////////////////////////////////////////////////////////////
// transmit engine: fills tb[] with  cmd, len_lo, len_hi, payload  then sends A5 + tb + chk
////////////////////////////////////////////////////////////
reg [7:0] tb [0:31];
reg [4:0] tx_n;
reg       tx_go;
reg [4:0] tx_i;
reg [7:0] tx_chk;
reg [2:0] tx_st;
localparam T_IDLE = 3'd0, T_PUT = 3'd1, T_WB = 3'd2, T_WD = 3'd3;
reg [1:0] tx_phase;                // 0 = sync byte, 1 = body, 2 = checksum
wire      tx_idle = (tx_st == T_IDLE);

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        tx_st <= T_IDLE; tx_send <= 1'b0; tx_data <= 8'd0; tx_i <= 5'd0; tx_chk <= 8'd0; tx_phase <= 2'd0;
    end else begin
        tx_send <= 1'b0;
        case (tx_st)
        T_IDLE: if (tx_go) begin tx_phase <= 2'd0; tx_i <= 5'd0; tx_chk <= 8'd0; tx_st <= T_PUT; end
        T_PUT: begin
            if (!tx_busy) begin
                case (tx_phase)
                2'd0: tx_data <= 8'hA5;
                2'd1: begin tx_data <= tb[tx_i]; tx_chk <= tx_chk + tb[tx_i]; end
                default: tx_data <= tx_chk;
                endcase
                tx_send <= 1'b1;
                tx_st   <= T_WB;
            end
        end
        T_WB: if (tx_busy) tx_st <= T_WD;               // byte accepted
        T_WD: if (!tx_busy) begin                       // byte finished
            case (tx_phase)
            2'd0: begin tx_phase <= 2'd1; tx_st <= T_PUT; end
            2'd1: begin
                if (tx_i == tx_n - 1) tx_phase <= 2'd2; else tx_i <= tx_i + 1'b1;
                tx_st <= T_PUT;
            end
            default: tx_st <= T_IDLE;
            endcase
        end
        default: tx_st <= T_IDLE;
        endcase
    end
end

////////////////////////////////////////////////////////////
// frame parser
////////////////////////////////////////////////////////////
localparam P_SYNC = 3'd0, P_CMD = 3'd1, P_L0 = 3'd2, P_L1 = 3'd3, P_PAY = 3'd4, P_CHK = 3'd5;
reg [2:0]  pst;
reg [7:0]  cmd, chk;
reg [15:0] plen, pcnt;
reg [3:0]  wr_target;
reg [2:0]  wr_wb;
reg [15:0] wr_addr;
reg [31:0] wacc;
reg [2:0]  wbc;
reg [7:0]  pl [0:PL_BYTES-1];
reg [7:0]  ctrl_flags;
integer    xi;
reg [31:0] tmo;
reg        exec_req;
reg [7:0]  exec_cmd;
reg        frame_ok_r;
assign frame_ok_o = frame_ok_r;

wire [31:0] wword_full = wacc | ({24'd0, rx_data} << (8 * wbc));
wire        word_done  = (wbc + 3'd1 == wr_wb);

task automatic nak(input [7:0] status);
begin
    tb[0] <= 8'h81; tb[1] <= 8'd1; tb[2] <= 8'd0; tb[3] <= status; tx_n <= 5'd4; tx_go <= 1'b1;
end
endtask

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        pst <= P_SYNC; cmd <= 8'd0; chk <= 8'd0; plen <= 16'd0; pcnt <= 16'd0;
        wr_target <= 4'd0; wr_wb <= 3'd0; wr_addr <= 16'd0; wacc <= 32'd0; wbc <= 3'd0;
        ctrl_flags <= 8'd0; tmo <= 32'd0; exec_req <= 1'b0; exec_cmd <= 8'd0; frame_ok_r <= 1'b0;
        esn_ld_we <= 1'b0; esn_ld_sel <= 2'd0; esn_ld_addr <= {AW_LD{1'b0}}; esn_ld_data <= 16'sd0;
        rw_we <= 1'b0; rw_sel <= 1'b0; rw_addr <= {IW{1'b0}}; rw_data <= 18'sd0;
        ekf_cfg_we <= 1'b0; ekf_cfg_addr <= 6'd0; ukf_cfg_we <= 1'b0; ukf_cfg_addr <= 6'd0; cfg_data <= 32'sd0;
        ekf_lut_we <= 1'b0; ekf_lut_sel <= 1'b0; ukf_lut_we <= 1'b0; ukf_lut_sel <= 1'b0;
        lut_waddr <= 10'd0; lut_wdata <= 32'sd0;
        tx_go <= 1'b0; tx_n <= 5'd0;
        esn_start <= 1'b0; esn_clear <= 1'b0; ekf_init <= 1'b0; ekf_start <= 1'b0; ukf_start <= 1'b0;
    end else begin
        // default strobes (executor below may override: it owns esn_start/clear/init/starts and ld writes in STEP)
        exec_req   <= 1'b0;
        frame_ok_r <= 1'b0;
        esn_ld_we <= 1'b0; rw_we <= 1'b0; ekf_cfg_we <= 1'b0; ukf_cfg_we <= 1'b0;
        ekf_lut_we <= 1'b0; ukf_lut_we <= 1'b0;
        tx_go <= 1'b0;
        esn_start <= 1'b0; esn_clear <= 1'b0; ekf_init <= 1'b0; ekf_start <= 1'b0; ukf_start <= 1'b0;

        // watchdog: a half-received frame is dropped after TIMEOUT clocks without a byte
        if (rx_valid || pst == P_SYNC) tmo <= 32'd0;
        else if (tmo == TIMEOUT) begin pst <= P_SYNC; tmo <= 32'd0; end
        else tmo <= tmo + 1'b1;

        if (rx_valid) begin
            case (pst)
            P_SYNC: if (rx_data == 8'hA5) pst <= P_CMD;
            P_CMD:  begin cmd <= rx_data; chk <= rx_data; pst <= P_L0; end
            P_L0:   begin plen[7:0] <= rx_data; chk <= chk + rx_data; pst <= P_L1; end
            P_L1:   begin
                plen[15:8] <= rx_data; chk <= chk + rx_data; pcnt <= 16'd0; wbc <= 3'd0; wacc <= 32'd0;
                pst <= ({rx_data, plen[7:0]} == 16'd0) ? P_CHK : P_PAY;
            end
            P_PAY: begin
                chk  <= chk + rx_data;
                pcnt <= pcnt + 1'b1;
                if (pcnt + 1'b1 == plen) pst <= P_CHK;
                case (cmd)
                CMD_WRITE: begin
                    if      (pcnt == 16'd0) wr_target <= rx_data[3:0];
                    else if (pcnt == 16'd1) wr_wb     <= rx_data[2:0];
                    else if (pcnt == 16'd2) wr_addr[7:0]  <= rx_data;
                    else if (pcnt == 16'd3) wr_addr[15:8] <= rx_data;
                    else if (wr_wb != 3'd0) begin
                        if (word_done) begin
                            wacc <= 32'd0; wbc <= 3'd0; wr_addr <= wr_addr + 1'b1;
                            case (wr_target)
                            4'd0, 4'd1, 4'd2, 4'd3: begin
                                esn_ld_we <= 1'b1; esn_ld_sel <= wr_target[1:0];
                                esn_ld_addr <= wr_addr[AW_LD-1:0]; esn_ld_data <= wword_full[15:0];
                            end
                            4'd4, 4'd5: begin
                                rw_we <= 1'b1; rw_sel <= wr_target[0]; rw_addr <= wr_addr[IW-1:0]; rw_data <= wword_full[17:0];
                            end
                            4'd8:  begin ekf_cfg_we <= 1'b1; ekf_cfg_addr <= wr_addr[5:0]; cfg_data <= wword_full; end
                            4'd9:  begin ukf_cfg_we <= 1'b1; ukf_cfg_addr <= wr_addr[5:0]; cfg_data <= wword_full; end
                            4'd10: begin ekf_lut_we <= 1'b1; ekf_lut_sel <= 1'b0; lut_waddr <= wr_addr[9:0]; lut_wdata <= wword_full; end
                            4'd11: begin ekf_lut_we <= 1'b1; ekf_lut_sel <= 1'b1; lut_waddr <= wr_addr[9:0]; lut_wdata <= wword_full; end
                            4'd12: begin ukf_lut_we <= 1'b1; ukf_lut_sel <= 1'b0; lut_waddr <= wr_addr[9:0]; lut_wdata <= wword_full; end
                            4'd13: begin ukf_lut_we <= 1'b1; ukf_lut_sel <= 1'b1; lut_waddr <= wr_addr[9:0]; lut_wdata <= wword_full; end
                            default: ;
                            endcase
                        end else begin
                            wacc <= wword_full; wbc <= wbc + 1'b1;
                        end
                    end
                end
                CMD_CTRL: if (pcnt == 16'd0) ctrl_flags <= rx_data;
                CMD_STEP: if (pcnt < PL_BYTES) pl[pcnt[4:0]] <= rx_data;
                default: ;
                endcase
            end
            P_CHK: begin
                pst <= P_SYNC;
                if (rx_data == chk) begin
                    frame_ok_r <= 1'b1;
                    if (cmd == CMD_WRITE || cmd == CMD_CTRL || cmd == CMD_STEP || cmd == CMD_PING) begin
                        exec_req <= 1'b1; exec_cmd <= cmd;
                    end else nak(8'd2);
                end else nak(8'd1);
            end
            default: pst <= P_SYNC;
            endcase
        end

        ////////////////////////////////////////////////////////
        // executor strobes (set from the executor FSM below)
        ////////////////////////////////////////////////////////
        if (x_esn_ld) begin esn_ld_we <= 1'b1; esn_ld_sel <= 2'd2; esn_ld_addr <= x_ld_addr; esn_ld_data <= x_ld_data; end
        if (x_kf_we)  begin
            cfg_data <= x_kf_data;
            if (x_kf_sel) ukf_cfg_we <= 1'b1; else ekf_cfg_we <= 1'b1;
            ekf_cfg_addr <= x_kf_addr[5:0]; ukf_cfg_addr <= x_kf_addr[5:0];
        end
        if (x_start)  begin esn_start <= 1'b1; ekf_start <= 1'b1; ukf_start <= 1'b1; end
        if (x_clear)  esn_clear <= 1'b1;
        if (x_init)   ekf_init  <= 1'b1;
        if (x_tx)     begin
            for (xi = 0; xi < 24; xi = xi + 1) tb[xi] <= x_tb[xi];
            tx_n <= x_txn; tx_go <= 1'b1;
        end
    end
end

////////////////////////////////////////////////////////////
// executor FSM (runs after a good frame)
////////////////////////////////////////////////////////////
integer xj;
localparam X_IDLE = 4'd0, X_LD = 4'd1, X_KF = 4'd2, X_GO = 4'd3, X_WAIT = 4'd4, X_RESP = 4'd5,
           X_CLR = 4'd6, X_CLRW = 4'd7, X_ACK = 4'd8, X_TXW = 4'd9, X_INFO = 4'd10, X_INIT = 4'd11;
reg [3:0]  xst;
reg [4:0]  xk;
// strobes into the parser block above
reg        x_esn_ld, x_kf_we, x_kf_sel, x_start, x_clear, x_init, x_tx;
reg [AW_LD-1:0] x_ld_addr; reg signed [15:0] x_ld_data;
reg [5:0]  x_kf_addr; reg signed [31:0] x_kf_data;
reg [7:0]  x_tb [0:23]; reg [4:0] x_txn;

reg        esn_done_q;
always @(posedge clk or negedge rst_n) if (!rst_n) esn_done_q <= 1'b0; else esn_done_q <= esn_done;
wire       esn_done_rise = esn_done & ~esn_done_q;

reg [23:0] cyc_esn; reg [15:0] cyc_ekf, cyc_ukf;
reg        run_esn, run_ekf, run_ukf;
reg signed [31:0] ekf_l, ukf_l;
reg [7:0]  status_r;

assign busy_o     = (xst != X_IDLE);
assign ovf_seen_o = ovf_seen;

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        xst <= X_IDLE; xk <= 5'd0;
        x_esn_ld <= 1'b0; x_kf_we <= 1'b0; x_kf_sel <= 1'b0; x_start <= 1'b0; x_clear <= 1'b0; x_init <= 1'b0; x_tx <= 1'b0;
        x_ld_addr <= {AW_LD{1'b0}}; x_ld_data <= 16'sd0; x_kf_addr <= 6'd0; x_kf_data <= 32'sd0; x_txn <= 5'd0;
        esn_seen <= 1'b0; ekf_seen <= 1'b0; ukf_seen <= 1'b0; soc_seen <= 1'b0; soh_seen <= 1'b0; ovf_seen <= 1'b0;
        cyc_esn <= 24'd0; cyc_ekf <= 16'd0; cyc_ukf <= 16'd0; run_esn <= 1'b0; run_ekf <= 1'b0; run_ukf <= 1'b0;
        soc_l <= 16'sd0; soh_l <= 16'sd0; step_l <= {SW{1'b0}}; ekf_l <= 32'sd0; ukf_l <= 32'sd0; status_r <= 8'd0;
        for (xj = 0; xj < 24; xj = xj + 1) x_tb[xj] <= 8'd0;
    end else begin
        x_esn_ld <= 1'b0; x_kf_we <= 1'b0; x_start <= 1'b0; x_clear <= 1'b0; x_init <= 1'b0; x_tx <= 1'b0;

        // ---- result capture / cycle counters (free-running) ----
        if (soc_valid) begin soc_l <= soc; step_l <= soc_step; soc_seen <= 1'b1; end
        if (soh_valid) begin soh_l <= soh; soh_seen <= 1'b1; end
        if (ovf_out | dense_err) ovf_seen <= 1'b1;
        if (esn_done_rise) begin esn_seen <= 1'b1; run_esn <= 1'b0; end
        if (ekf_done) begin ekf_seen <= 1'b1; ekf_l <= ekf_soc; run_ekf <= 1'b0; end
        if (ukf_done) begin ukf_seen <= 1'b1; ukf_l <= ukf_soc; run_ukf <= 1'b0; end
        if (run_esn) cyc_esn <= cyc_esn + 1'b1;
        if (run_ekf) cyc_ekf <= cyc_ekf + 1'b1;
        if (run_ukf) cyc_ukf <= cyc_ukf + 1'b1;

        case (xst)
        X_IDLE: if (exec_req) begin
            xk <= 5'd0;
            case (exec_cmd)
            CMD_WRITE: begin status_r <= 8'd0; xst <= X_ACK; end
            CMD_CTRL:  begin status_r <= 8'd0; xst <= X_CLR; end
            CMD_STEP:  begin xst <= X_LD; end
            CMD_PING:  xst <= X_INFO;
            default:   xst <= X_IDLE;
            endcase
        end

        // ---- STEP: input vector into ESN input RAM at timestep*N_IN + i ----
        X_LD: begin
            x_esn_ld  <= 1'b1;
            x_ld_addr <= (timestep * N_IN) + xk;
            x_ld_data <= {pl[2*xk + 1], pl[2*xk]};
            if (xk == N_IN - 1) begin xk <= 5'd0; xst <= X_KF; end else xk <= xk + 1'b1;
        end
        // ---- EKF / UKF current and voltage registers (EKF 20/21, UKF 5/6) ----
        X_KF: begin
            x_kf_we <= 1'b1;
            case (xk[1:0])
            2'd0: begin x_kf_sel <= 1'b0; x_kf_addr <= 6'd20; x_kf_data <= {pl[2*N_IN+3], pl[2*N_IN+2], pl[2*N_IN+1], pl[2*N_IN+0]}; end
            2'd1: begin x_kf_sel <= 1'b1; x_kf_addr <= 6'd5;  x_kf_data <= {pl[2*N_IN+3], pl[2*N_IN+2], pl[2*N_IN+1], pl[2*N_IN+0]}; end
            2'd2: begin x_kf_sel <= 1'b0; x_kf_addr <= 6'd21; x_kf_data <= {pl[2*N_IN+7], pl[2*N_IN+6], pl[2*N_IN+5], pl[2*N_IN+4]}; end
            default: begin x_kf_sel <= 1'b1; x_kf_addr <= 6'd6;  x_kf_data <= {pl[2*N_IN+7], pl[2*N_IN+6], pl[2*N_IN+5], pl[2*N_IN+4]}; end
            endcase
            if (xk[1:0] == 2'd3) begin xk <= 5'd0; xst <= X_GO; end else xk <= xk + 1'b1;
        end
        X_GO: begin   // one cycle after the last cfg write: start everything together
            x_start <= 1'b1;
            esn_seen <= 1'b0; ekf_seen <= 1'b0; ukf_seen <= 1'b0; soc_seen <= 1'b0; soh_seen <= 1'b0;
            cyc_esn <= 24'd1; cyc_ekf <= 16'd1; cyc_ukf <= 16'd1; run_esn <= 1'b1; run_ekf <= 1'b1; run_ukf <= 1'b1;
            xst <= X_WAIT;
        end
        X_WAIT: if (esn_seen && ekf_seen && ukf_seen && soc_seen) xst <= X_RESP;
        X_RESP: begin
            x_tb[0]  <= 8'h83; x_tb[1] <= 8'd21; x_tb[2] <= 8'd0;
            x_tb[3]  <= {{(8-SW){1'b0}}, step_l};
            x_tb[4]  <= {6'b000000, ovf_seen, soh_seen};
            x_tb[5]  <= soc_l[7:0];    x_tb[6]  <= soc_l[15:8];
            x_tb[7]  <= ekf_l[7:0];    x_tb[8]  <= ekf_l[15:8];  x_tb[9]  <= ekf_l[23:16];  x_tb[10] <= ekf_l[31:24];
            x_tb[11] <= ukf_l[7:0];    x_tb[12] <= ukf_l[15:8];  x_tb[13] <= ukf_l[23:16];  x_tb[14] <= ukf_l[31:24];
            x_tb[15] <= soh_l[7:0];    x_tb[16] <= soh_l[15:8];
            x_tb[17] <= cyc_esn[7:0];  x_tb[18] <= cyc_esn[15:8]; x_tb[19] <= cyc_esn[23:16];
            x_tb[20] <= cyc_ekf[7:0];  x_tb[21] <= cyc_ekf[15:8];
            x_tb[22] <= cyc_ukf[7:0];  x_tb[23] <= cyc_ukf[15:8];
            x_txn <= 5'd24; x_tx <= 1'b1; xst <= X_TXW;
        end

        // ---- CTRL ----
        X_CLR: begin
            if (ctrl_flags[0]) x_clear <= 1'b1;
            if (ctrl_flags[1]) x_init  <= 1'b1;
            if (ctrl_flags[0]) begin ovf_seen <= 1'b0; end
            xk <= 5'd0; xst <= X_CLRW;
        end
        X_CLRW: begin   // give the clear a few cycles to start, then wait until the core is idle
            if (xk < 5'd4) xk <= xk + 1'b1;
            else if (!esn_busy) xst <= X_ACK;
        end

        X_ACK: begin
            x_tb[0] <= 8'h81; x_tb[1] <= 8'd1; x_tb[2] <= 8'd0; x_tb[3] <= status_r;
            x_txn <= 5'd4; x_tx <= 1'b1; xst <= X_TXW;
        end
        X_INFO: begin
            x_tb[0] <= 8'h84; x_tb[1] <= 8'd8; x_tb[2] <= 8'd0;
            x_tb[3] <= "E"; x_tb[4] <= "P"; x_tb[5] <= 8'd1; x_tb[6] <= n_in_w;
            x_tb[7] <= n_res_w[7:0]; x_tb[8] <= n_res_w[15:8]; x_tb[9] <= t_max_w[7:0]; x_tb[10] <= t_max_w[15:8];
            x_txn <= 5'd11; x_tx <= 1'b1; xst <= X_TXW;
        end
        X_TXW: if (!x_tx && tx_idle && !tx_go) xst <= X_IDLE;
        default: xst <= X_IDLE;
        endcase
    end
end

endmodule
