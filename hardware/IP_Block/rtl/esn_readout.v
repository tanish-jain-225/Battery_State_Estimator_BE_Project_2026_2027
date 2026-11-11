`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////
// esn_readout.v (Rev 2: run-time loadable weights) -- streaming linear SOC / SOH readout for esn_top
//
// Sits beside esn_top and listens to its state stream (x_out / x_valid):
// each reservoir update emits x_0(t+1) ... x_99(t+1), one per x_valid pulse,
// in neuron order. No state buffer is needed:
//
//   SOC(t) = sum_i w_soc[i] * x_i(t) + c_soc                 (every step)
//   SOH    = (1/64) sum_t sum_i w_soh[i] * x_i(t) + c_soh    (once per cycle)
//          = w_soh . mean_t x(t) + c_soh                     (PCA folded in)
//
// Arithmetic (bit-exact with export_readout.py):
//   x : int16 Q6.10      w, c : int18 Q4.14 (ROM file: w[0..99], c at addr 100)
//   SOC = sat16( ((acc_soc + 2^9)  >>> 10) + c_soc )   -> Q2.14
//   SOH = sat16( ((acc_soh + 2^15) >>> 16) + c_soh )   -> Q2.14
//
// Pipeline: S1 register x + weights, S2 multiply (DSP), S3 accumulate,
// S4 round + offset + saturate. x_valid pulses are ~428 cycles apart, so
// the pipeline never overlaps two neurons of the same step.
//
// clear : synchronous; reset the neuron / step counters and accumulators
//         (pulse it before the first step of a new discharge cycle).
//////////////////////////////////////////////////////////////////////////////
module esn_readout #(
    parameter N_RES      = 100,
    parameter T_STEPS    = 64,                 // power of two; SOH = mean over T_STEPS steps
    parameter IW         = $clog2(N_RES + 1),  // weight / neuron index width
    parameter SW         = (T_STEPS > 1) ? $clog2(T_STEPS) : 1,
    parameter SOC_FILE   = "",
    parameter SOH_FILE   = ""
)(
    input  wire               clk,
    input  wire               rst_n,
    input  wire               clear,
    input  wire signed [15:0] x_in,       // from esn_top.x_out
    input  wire               x_valid,    // from esn_top.x_valid
    // run-time weight load (rw_sel 0 = SOC ROM, 1 = SOH ROM; address 0..N_RES, N_RES = offset c)
    input  wire               rw_we,
    input  wire               rw_sel,
    input  wire [IW-1:0]      rw_addr,
    input  wire signed [17:0] rw_data,
    output reg  signed [15:0] soc,        // Q2.14
    output reg                soc_valid,  // 1-cycle pulse per step
    output reg  [SW-1:0]      soc_step,   // step index of the current soc
    output reg  signed [15:0] soh,        // Q2.14
    output reg                soh_valid   // 1-cycle pulse after step 63
);

// ---------------- weight ROMs (distributed, async read) ----------------
reg signed [17:0] rom_soc [0:N_RES];
reg signed [17:0] rom_soh [0:N_RES];
integer ri;
initial begin
    for (ri = 0; ri <= N_RES; ri = ri + 1) begin rom_soc[ri] = 18'sd0; rom_soh[ri] = 18'sd0; end
    if (SOC_FILE != "") $readmemh(SOC_FILE, rom_soc);
    if (SOH_FILE != "") $readmemh(SOH_FILE, rom_soh);
end
always @(posedge clk) begin
    if (rw_we && !rw_sel) rom_soc[rw_addr] <= rw_data;
    if (rw_we &&  rw_sel) rom_soh[rw_addr] <= rw_data;
end
wire signed [17:0] c_soc = rom_soc[N_RES];
wire signed [17:0] c_soh = rom_soh[N_RES];

// ---------------- counters ----------------
reg [IW-1:0] idx;   // neuron index 0..N_RES-1
reg [SW-1:0] step;  // timestep 0..T_STEPS-1

// ---------------- S1: capture ----------------
reg               v1, last1, endc1;
reg signed [15:0] x1;
reg signed [17:0] ws1, wh1;
reg [SW-1:0]      step1;

// ---------------- S2: multiply ----------------
reg               v2, last2, endc2;
reg signed [33:0] ps2, ph2;
reg [SW-1:0]      step2;

// ---------------- S3: accumulate ----------------
reg signed [39:0] acc_soc;
reg signed [47:0] acc_soh;
reg               fin_soc3, fin_soh3;
reg signed [39:0] sum_soc3;
reg signed [47:0] sum_soh3;
reg [SW-1:0]      step3;

wire signed [39:0] acc_soc_n = acc_soc + {{6{ps2[33]}}, ps2};
wire signed [47:0] acc_soh_n = acc_soh + {{14{ph2[33]}}, ph2};

// ---------------- S4: round, offset, saturate ----------------
wire signed [39:0] soc_r = (sum_soc3 + 40'sd512)   >>> 10;
localparam LT = $clog2(T_STEPS);     // T_STEPS must be a power of two
wire signed [47:0] soh_r = (sum_soh3 + (48'sd1 <<< (9 + LT))) >>> (10 + LT);   // T=64: (sum+2^15)>>>16
wire signed [39:0] soc_o = soc_r + {{22{c_soc[17]}}, c_soc};
wire signed [47:0] soh_o = soh_r + {{30{c_soh[17]}}, c_soh};

function signed [15:0] sat16_40(input signed [39:0] v);
    sat16_40 = (v >  40'sd32767) ? 16'sh7FFF :
               (v < -40'sd32768) ? 16'sh8000 : v[15:0];
endfunction
function signed [15:0] sat16_48(input signed [47:0] v);
    sat16_48 = (v >  48'sd32767) ? 16'sh7FFF :
               (v < -48'sd32768) ? 16'sh8000 : v[15:0];
endfunction

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        idx <= 0; step <= 0;
        v1 <= 0; last1 <= 0; endc1 <= 0; x1 <= 0; ws1 <= 0; wh1 <= 0; step1 <= 0;
        v2 <= 0; last2 <= 0; endc2 <= 0; ps2 <= 0; ph2 <= 0; step2 <= 0;
        acc_soc <= 0; acc_soh <= 0; fin_soc3 <= 0; fin_soh3 <= 0;
        sum_soc3 <= 0; sum_soh3 <= 0; step3 <= 0;
        soc <= 0; soh <= 0; soc_valid <= 0; soh_valid <= 0; soc_step <= 0;
    end else if (clear) begin
        idx <= 0; step <= 0;
        v1 <= 0; v2 <= 0; fin_soc3 <= 0; fin_soh3 <= 0;
        acc_soc <= 0; acc_soh <= 0;
        soc_valid <= 0; soh_valid <= 0;
    end else begin
        // S1
        v1 <= x_valid;
        if (x_valid) begin
            x1    <= x_in;
            ws1   <= rom_soc[idx];
            wh1   <= rom_soh[idx];
            last1 <= (idx == N_RES - 1);
            endc1 <= (idx == N_RES - 1) && (step == T_STEPS - 1);
            step1 <= step;
            if (idx == N_RES - 1) begin
                idx  <= 0;
                step <= (step == T_STEPS - 1) ? {SW{1'b0}} : step + 1'b1;
            end else
                idx <= idx + 1'b1;
        end
        // S2
        v2 <= v1;
        if (v1) begin
            ps2 <= ws1 * x1;
            ph2 <= wh1 * x1;
            last2 <= last1; endc2 <= endc1; step2 <= step1;
        end
        // S3
        fin_soc3 <= v2 & last2;
        fin_soh3 <= v2 & endc2;
        if (v2) begin
            step3 <= step2;
            if (last2) begin
                sum_soc3 <= acc_soc_n; acc_soc <= 0;
            end else
                acc_soc <= acc_soc_n;
            if (endc2) begin
                sum_soh3 <= acc_soh_n; acc_soh <= 0;
            end else
                acc_soh <= acc_soh_n;
        end
        // S4
        soc_valid <= fin_soc3;
        soh_valid <= fin_soh3;
        if (fin_soc3) begin soc <= sat16_40(soc_o); soc_step <= step3; end
        if (fin_soh3) soh <= sat16_48(soh_o);
    end
end

endmodule
