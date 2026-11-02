`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////
// ekf_core.v -- fixed-point 1-RC Thevenin EKF for battery SOC (Rev 0.3)
//
// Rev 0.3: rounding moved into its own pipeline stage (rnd_r), and the
//          32-bit saturation test done on the upper sum bits instead of two
//          66-bit comparisons. Same arithmetic, still bit-exact; a MAC
//          micro-op now takes 5 cycles.
//
// Rev 0.2: MAC pipelined for timing (operand register + 2 multiplier
//          stages that Vivado packs into the DSP48 M/P registers). The
//          arithmetic is unchanged, so results stay bit-exact with Rev 0.1;
//          each MAC micro-op now takes 4 cycles instead of 2.
//
// Same design style as the ESN core: ONE time-multiplexed multiply-accumulate
// unit, a small FSM sequencing a fixed micro-program, ROM lookup tables
// (OCV and dOCV/dSOC, like tanh_lut), plus a sequential divider for the
// Kalman gain. Bit-exact reference: ekf_fixed.py (run_ekf_fixed).
//
// Formats (32-bit signed): Q2.30 for SOC, P, Q, R, S, a, b, kcc, R0;
//                          Q4.28 for I, V, OCV, V1, h0, innovation, K.
//
// MAC micro-op:  rd = sat32( rc +/- ((ra*rb + 2^(s-1)) >>> s) ),  s in {26,28,30}
//
// Interface
//   cfg_we/cfg_addr/cfg_data : write any register (constants, x0 = SOC0,
//                              inputs I (addr 20) and Vmeas (addr 21))
//   init  : one-cycle pulse, sets V1 = 0, P00 = P11 = P0, P01 = 0
//   start : one-cycle pulse, runs one predict+update step
//   done  : one-cycle pulse when the step has finished; soc_out valid
//////////////////////////////////////////////////////////////////////////////
module ekf_core #(
    parameter OCV_FILE   = "ocv_lut.mem",
    parameter SLOPE_FILE = "slope_lut.mem"
)(
    input  wire               clk,
    input  wire               rst_n,
    input  wire               cfg_we,
    input  wire [4:0]         cfg_addr,
    input  wire signed [31:0] cfg_data,
    input  wire               init,
    input  wire               start,
    output reg                done,
    output wire signed [31:0] soc_out,
    output wire               busy
);

// ---------------- register map ----------------
localparam R_X0 = 5'd0,  R_V1 = 5'd1,  R_P00 = 5'd2,  R_P01 = 5'd3,  R_P11 = 5'd4,
           R_X0P = 5'd5, R_V1P = 5'd6, R_P00P = 5'd7, R_P01P = 5'd8, R_P11P = 5'd9,
           R_TMP = 5'd10, R_OCV = 5'd11, R_H0 = 5'd12, R_YP = 5'd13, R_INN = 5'd14,
           R_PH0 = 5'd15, R_PH1 = 5'd16, R_S = 5'd17, R_K0 = 5'd18, R_K1 = 5'd19,
           R_I = 5'd20, R_VM = 5'd21, R_A = 5'd22, R_B = 5'd23, R_KCC = 5'd24,
           R_R0 = 5'd25, R_Q0 = 5'd26, R_Q1 = 5'd27, R_R = 5'd28, R_ONE = 5'd29,
           R_ZERO = 5'd30, R_P0 = 5'd31;

localparam signed [31:0] ONE30 = 32'sh4000_0000;
localparam signed [31:0] I32_MAX = 32'sh7FFF_FFFF;
localparam signed [31:0] I32_MIN = 32'sh8000_0000;

reg signed [31:0] rf [0:31];
assign soc_out = rf[R_X0];

// ---------------- micro-program ----------------
localparam OP_MAC = 2'd0, OP_LUT = 2'd1, OP_DIV = 2'd2;
localparam LAST_PC = 5'd21;

reg [4:0] pc;
reg [1:0] u_op;  reg [4:0] u_ra, u_rb, u_rc, u_rd;
reg [4:0] u_s;   reg u_sub, u_clamp;

always @(*) begin
    u_op = OP_MAC; u_ra = R_ZERO; u_rb = R_ZERO; u_rc = R_ZERO; u_rd = R_TMP;
    u_s = 5'd30; u_sub = 1'b0; u_clamp = 1'b0;
    case (pc)
    // ---- predict ----
    5'd0:  begin u_ra=R_KCC; u_rb=R_I;    u_rc=R_X0;   u_s=5'd28; u_rd=R_X0P;  end
    5'd1:  begin u_ra=R_A;   u_rb=R_V1;   u_rc=R_ZERO; u_s=5'd30; u_rd=R_TMP;  end
    5'd2:  begin u_ra=R_B;   u_rb=R_I;    u_rc=R_TMP;  u_s=5'd30; u_rd=R_V1P;  end
    5'd3:  begin u_ra=R_P00; u_rb=R_ONE;  u_rc=R_Q0;   u_s=5'd30; u_rd=R_P00P; end
    5'd4:  begin u_ra=R_A;   u_rb=R_P01;  u_rc=R_ZERO; u_s=5'd30; u_rd=R_P01P; end
    5'd5:  begin u_ra=R_A;   u_rb=R_P11;  u_rc=R_ZERO; u_s=5'd30; u_rd=R_TMP;  end
    5'd6:  begin u_ra=R_A;   u_rb=R_TMP;  u_rc=R_Q1;   u_s=5'd30; u_rd=R_P11P; end
    // ---- update ----
    5'd7:  begin u_op=OP_LUT; end                       // OCV, h0 <- LUT(x0p)
    5'd8:  begin u_ra=R_R0;  u_rb=R_I;    u_rc=R_OCV;  u_s=5'd30; u_rd=R_TMP;  end
    5'd9:  begin u_ra=R_V1P; u_rb=R_ONE;  u_rc=R_TMP;  u_s=5'd30; u_rd=R_YP;   end
    5'd10: begin u_ra=R_YP;  u_rb=R_ONE;  u_rc=R_VM;   u_s=5'd30; u_sub=1'b1; u_rd=R_INN; end
    5'd11: begin u_ra=R_P00P;u_rb=R_H0;   u_rc=R_P01P; u_s=5'd28; u_rd=R_PH0;  end
    5'd12: begin u_ra=R_P01P;u_rb=R_H0;   u_rc=R_P11P; u_s=5'd28; u_rd=R_PH1;  end
    5'd13: begin u_ra=R_H0;  u_rb=R_PH0;  u_rc=R_PH1;  u_s=5'd28; u_rd=R_TMP;  end
    5'd14: begin u_ra=R_TMP; u_rb=R_ONE;  u_rc=R_R;    u_s=5'd30; u_rd=R_S;    end
    5'd15: begin u_op=OP_DIV; u_ra=R_PH0; u_rb=R_S; u_rd=R_K0; end
    5'd16: begin u_op=OP_DIV; u_ra=R_PH1; u_rb=R_S; u_rd=R_K1; end
    5'd17: begin u_ra=R_K0;  u_rb=R_INN;  u_rc=R_X0P;  u_s=5'd26; u_clamp=1'b1; u_rd=R_X0; end
    5'd18: begin u_ra=R_K1;  u_rb=R_INN;  u_rc=R_V1P;  u_s=5'd28; u_rd=R_V1;   end
    5'd19: begin u_ra=R_K0;  u_rb=R_PH0;  u_rc=R_P00P; u_s=5'd28; u_sub=1'b1; u_rd=R_P00; end
    5'd20: begin u_ra=R_K0;  u_rb=R_PH1;  u_rc=R_P01P; u_s=5'd28; u_sub=1'b1; u_rd=R_P01; end
    5'd21: begin u_ra=R_K1;  u_rb=R_PH1;  u_rc=R_P11P; u_s=5'd28; u_sub=1'b1; u_rd=R_P11; end
    default: ;
    endcase
end

// ---------------- MAC datapath (FETCH -> MUL1 -> MUL2 -> MAC2) ----------------
reg  signed [31:0] opa_r, opb_r;
reg  signed [63:0] mul_p1, prod_r;
always @(posedge clk) begin          // no reset: lets Vivado use DSP48 MREG/PREG
    mul_p1 <= opa_r * opb_r;
    prod_r <= mul_p1;
end
reg  signed [31:0] c_r;
reg  [4:0]         s_r;
reg                sub_r, clamp_r;

reg  signed [65:0] rounded, rnd_r;
reg  signed [65:0] sum66;
reg  signed [31:0] mac_res;

always @(*) begin                    // stage S_RND: rnd_r <= rounded
    case (s_r)
        5'd26:   rounded = ($signed({{2{prod_r[63]}}, prod_r}) + 66'sd33554432 ) >>> 26;
        5'd28:   rounded = ($signed({{2{prod_r[63]}}, prod_r}) + 66'sd134217728) >>> 28;
        default: rounded = ($signed({{2{prod_r[63]}}, prod_r}) + 66'sd536870912) >>> 30;
    endcase
end

always @(*) begin                    // stage S_MAC2: add/sub, saturate, clamp
    sum66 = sub_r ? ($signed({{34{c_r[31]}}, c_r}) - rnd_r)
                  : ($signed({{34{c_r[31]}}, c_r}) + rnd_r);
    // fits in 32 bits  <=>  bits [65:31] are all equal
    if (!sum66[65] && (|sum66[64:31]))      mac_res = I32_MAX;   // > 2^31-1
    else if (sum66[65] && !(&sum66[64:31])) mac_res = I32_MIN;   // < -2^31
    else                                    mac_res = sum66[31:0];
    if (clamp_r) begin
        if (mac_res < 0)          mac_res = 32'sd0;
        else if (mac_res > ONE30) mac_res = ONE30;
    end
end

// ---------------- OCV / slope ROMs (index = top 10 fraction bits of x0p) ----------------
wire signed [31:0] x0p_sh = rf[R_X0P] >>> 20;
wire [9:0] lut_addr = (rf[R_X0P][31])        ? 10'd0 :
                      (x0p_sh > 32'sd1023)   ? 10'd1023 : x0p_sh[9:0];
reg signed [31:0] ocv_rom   [0:1023];
reg signed [31:0] slope_rom [0:1023];
reg signed [31:0] ocv_q, slope_q;
initial begin
    $readmemh(OCV_FILE, ocv_rom);
    $readmemh(SLOPE_FILE, slope_rom);
end
always @(posedge clk) begin
    ocv_q   <= ocv_rom[lut_addr];
    slope_q <= slope_rom[lut_addr];
end

// ---------------- sequential divider: q = sat32((n << 28) / d), trunc toward 0 ----------------
reg  [59:0] div_num;
reg  [31:0] div_den;
reg  [32:0] div_rem;
reg  [59:0] div_quo;
reg  [5:0]  div_cnt;
reg         div_neg;
wire [32:0] rem_sh  = {div_rem[31:0], div_num[59]};
wire        rem_ge  = (rem_sh >= {1'b0, div_den});
wire [31:0] abs_ra  = rf[u_ra][31] ? (~rf[u_ra] + 32'd1) : rf[u_ra];
wire [31:0] abs_rb  = rf[u_rb][31] ? (~rf[u_rb] + 32'd1) : rf[u_rb];
reg  signed [31:0] div_res;
always @(*) begin
    if (!div_neg) div_res = (div_quo > 60'd2147483647) ? I32_MAX : $signed(div_quo[31:0]);
    else          div_res = (div_quo > 60'd2147483648) ? I32_MIN : $signed(~div_quo[31:0] + 32'd1);
end

// ---------------- control FSM ----------------
localparam S_IDLE = 4'd0, S_FETCH = 4'd1, S_MAC2 = 4'd2, S_LUT2 = 4'd3,
           S_DIV = 4'd4, S_DIVW = 4'd5, S_DONE = 4'd6, S_MUL1 = 4'd7, S_MUL2 = 4'd8,
           S_RND = 4'd9;
reg [3:0] state;
reg [4:0] rd_r;
assign busy = (state != S_IDLE);

integer k;
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        state <= S_IDLE; pc <= 5'd0; done <= 1'b0;
        opa_r <= 32'sd0; opb_r <= 32'sd0; rnd_r <= 66'sd0; c_r <= 32'sd0; s_r <= 5'd30; sub_r <= 1'b0; clamp_r <= 1'b0;
        rd_r <= 5'd0; div_num <= 60'd0; div_den <= 32'd1; div_rem <= 33'd0;
        div_quo <= 60'd0; div_cnt <= 6'd0; div_neg <= 1'b0;
        for (k = 0; k < 32; k = k + 1) rf[k] <= 32'sd0;
        rf[R_ONE] <= ONE30;
    end else begin
        done <= 1'b0;
        if (cfg_we && state == S_IDLE) rf[cfg_addr] <= cfg_data;
        case (state)
        S_IDLE: begin
            if (init) begin
                rf[R_V1] <= 32'sd0; rf[R_P00] <= rf[R_P0];
                rf[R_P01] <= 32'sd0; rf[R_P11] <= rf[R_P0];
            end else if (start) begin
                pc <= 5'd0; state <= S_FETCH;
            end
        end
        S_FETCH: begin
            rd_r <= u_rd;
            case (u_op)
            OP_MAC: begin
                opa_r   <= rf[u_ra];
                opb_r   <= rf[u_rb];
                c_r     <= rf[u_rc];
                s_r     <= u_s; sub_r <= u_sub; clamp_r <= u_clamp;
                state   <= S_MUL1;
            end
            OP_LUT: state <= S_LUT2;       // ROM samples lut_addr on this edge
            default: begin                 // OP_DIV
                div_num <= {abs_ra, 28'd0};
                div_den <= abs_rb;
                div_neg <= rf[u_ra][31] ^ rf[u_rb][31];
                div_rem <= 33'd0; div_quo <= 60'd0; div_cnt <= 6'd60;
                state   <= S_DIV;
            end
            endcase
        end
        S_MUL1: state <= S_MUL2;           // mul_p1 <= opa_r*opb_r
        S_MUL2: state <= S_RND;            // prod_r <= mul_p1
        S_RND:  begin rnd_r <= rounded; state <= S_MAC2; end
        S_MAC2: begin
            rf[rd_r] <= mac_res;
            if (pc == LAST_PC) state <= S_DONE;
            else begin pc <= pc + 5'd1; state <= S_FETCH; end
        end
        S_LUT2: begin
            rf[R_OCV] <= ocv_q; rf[R_H0] <= slope_q;
            pc <= pc + 5'd1; state <= S_FETCH;
        end
        S_DIV: begin
            div_rem <= rem_ge ? (rem_sh - {1'b0, div_den}) : rem_sh;
            div_quo <= {div_quo[58:0], rem_ge};
            div_num <= {div_num[58:0], 1'b0};
            div_cnt <= div_cnt - 6'd1;
            if (div_cnt == 6'd1) state <= S_DIVW;
        end
        S_DIVW: begin
            rf[rd_r] <= div_res;
            pc <= pc + 5'd1; state <= S_FETCH;
        end
        S_DONE: begin
            done <= 1'b1; state <= S_IDLE;
        end
        default: state <= S_IDLE;
        endcase
        rf[R_ZERO] <= 32'sd0;              // constants are read-only
        rf[R_ONE]  <= ONE30;
    end
end

endmodule
