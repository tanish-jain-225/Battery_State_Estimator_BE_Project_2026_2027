`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: Vivekanand Education Society's Institute Of Technology
// Engineer: Nambiar Akshay
// 
// Design Name: 
// Module Name: reservoir_controller
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Revision 0.02 - No functional change. Added in-line documentation of
//                 the exact neuron_start pulse timing, and added
//                 SIMULATION-only watchdogs: one flags if neuron_done
//                 never arrives within a bounded number of cycles after
//                 neuron_start, and another flags if neuron_start is
//                 ever asserted for more/less than exactly one cycle.
// Revision 0.03 - Removed the TEMPORARY DEBUG per-cycle $display trace
//                 and the FINISHED-entry $display. Cycle-by-cycle
//                 tracing confirmed the neuron_start pulse timing
//                 documented below is correct: esn_neuron sits idle in
//                 S_IDLE for several cycles before each new pulse
//                 arrives, so it never misses the 1-cycle start pulse.
//                 The actual bug that could produce wrong reservoir
//                 state was NOT in this module -- see
//                 mac_accum_q6_10.v revision 0.02 (sticky, non-pulsing
//                 result_valid). No functional change here beyond
//                 debug removal.
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////

module reservoir_controller
#(
    parameter N_RES = 100
)
(
    input  wire clk,
    input  wire rst_n,

    //------------------------------------------------------
    // Global Control
    //------------------------------------------------------

    input  wire start,
    output reg  done,
    output reg  reservoir_busy,

    //------------------------------------------------------
    // ESN Neuron Interface
    //------------------------------------------------------

    output reg neuron_start,
    input  wire neuron_done,

    //------------------------------------------------------
    // Reservoir Address
    //------------------------------------------------------

    output reg [$clog2(N_RES)-1:0] neuron_idx,

    //------------------------------------------------------
    // Store Enable
    //------------------------------------------------------

    output reg store_en
);

////////////////////////////////////////////////////////////
// FSM States
////////////////////////////////////////////////////////////
//
//   0 = IDLE
//   1 = START
//   2 = WAIT_DONE
//   3 = STORE
//   4 = NEXT
//   5 = FINISHED
////////////////////////////////////////////////////////////

localparam IDLE      = 3'd0;
localparam START     = 3'd1;
localparam WAIT_DONE = 3'd2;
localparam STORE     = 3'd3;
localparam NEXT      = 3'd4;
localparam FINISHED  = 3'd5;

reg [2:0] state;
reg [2:0] next_state;

////////////////////////////////////////////////////////////
// State Register
////////////////////////////////////////////////////////////

always @(posedge clk or negedge rst_n)
begin

    if(!rst_n)
        state <= IDLE;
    else
        state <= next_state;

end 

////////////////////////////////////////////////////////////
// Next State Logic
////////////////////////////////////////////////////////////

always @(*)
begin

    next_state = state;

    case(state)

        //------------------------------------------
        IDLE:
        //------------------------------------------
        begin
            if(start)
                next_state = START;
        end

        //------------------------------------------
        START:
        //------------------------------------------
        begin
            next_state = WAIT_DONE;
        end

        //------------------------------------------
        WAIT_DONE:
        //------------------------------------------
        begin
            if(neuron_done)
                next_state = STORE;
        end

        //------------------------------------------
        STORE:
        //------------------------------------------
        begin
            next_state = NEXT;
        end

        //------------------------------------------
        NEXT:
        //------------------------------------------
        begin
            if(neuron_idx == N_RES-1)
                next_state = FINISHED;
            else
                next_state = START;
        end

        //------------------------------------------
        FINISHED:
        //------------------------------------------
        begin
            if(!start)
                next_state = IDLE;
        end

        default:
            next_state = IDLE;

    endcase

end      

////////////////////////////////////////////////////////////
// Output Logic & Neuron Counter
////////////////////////////////////////////////////////////
//
// PULSE TIMING:
//
//   Cycle N   : state == START.
//               This always block matches case(state)==START and
//               registers neuron_start <= 1'b1.
//               (Simultaneously, the next-state block above --
//               combinationally reading the SAME registered `state`
//               -- computes next_state = WAIT_DONE.)
//
//   Cycle N+1 : Both non-blocking assignments from cycle N land here:
//                 state        becomes WAIT_DONE
//                 neuron_start becomes 1'b1
//               So esn_neuron's `start` input is high during the
//               exact same cycle the controller's own `state` reads
//               back as WAIT_DONE (2).
//
//   Cycle N+2 : neuron_start returns to 1'b0 (default at top of the
//               else branch below; WAIT_DONE's case arm does not
//               re-assert it). So neuron_start is a clean single-
//               cycle pulse.
//
// Confirmed by simulation trace: esn_neuron reaches S_IDLE several
// cycles before this pulse is issued for the next neuron (STORE ->
// NEXT -> START takes 3 cycles after neuron_done is seen), so the
// pulse is never missed.
////////////////////////////////////////////////////////////

always @(posedge clk or negedge rst_n)
begin

    if(!rst_n)
    begin

        neuron_idx     <= 0;

        neuron_start   <= 1'b0;
        store_en       <= 1'b0;

        done           <= 1'b0;
        reservoir_busy <= 1'b0;

    end

    else
    begin

        //--------------------------------------------------
        // Default Outputs
        //--------------------------------------------------

        neuron_start <= 1'b0;
        store_en     <= 1'b0;

        //--------------------------------------------------
        // FSM Outputs
        //--------------------------------------------------

        case(state)

        //----------------------------------------------
        // IDLE
        //----------------------------------------------
        IDLE:
        begin

            neuron_idx     <= 0;
            done           <= 1'b0;
            reservoir_busy <= 1'b0;

        end

        //----------------------------------------------
        // START
        //----------------------------------------------
        START:
        begin

            neuron_start   <= 1'b1;
            reservoir_busy <= 1'b1;

        end

        //----------------------------------------------
        // WAIT
        //----------------------------------------------
        WAIT_DONE:
        begin

            reservoir_busy <= 1'b1;

        end

        //----------------------------------------------
        // STORE
        //----------------------------------------------
        STORE:
        begin

            store_en       <= 1'b1;
            reservoir_busy <= 1'b1;

        end

        //----------------------------------------------
        // NEXT
        //----------------------------------------------
        NEXT:
        begin

            reservoir_busy <= 1'b1;

            if(neuron_idx < N_RES-1)
                neuron_idx <= neuron_idx + 1;

        end

        //----------------------------------------------
        // FINISHED
        //----------------------------------------------
        FINISHED:
        begin

            done           <= 1'b1;
            reservoir_busy <= 1'b0;

        end

        endcase

    end

end

/////////////////////////////////////////////////////////
// Simulation Watchdogs (only for simulation)
/////////////////////////////////////////////////////////
// These exist purely to make a neuron_done stall diagnosable
// from this module's own waveform, without hand-decoding state
// values every time.
/////////////////////////////////////////////////////////

`ifdef SIMULATION

    //----------------------------------------------------
    // Watchdog 1: neuron_start must be exactly a 1-cycle pulse
    //----------------------------------------------------
    reg neuron_start_d1;

    always @(posedge clk) neuron_start_d1 <= neuron_start;

    always @(posedge clk) begin
        if (rst_n) begin
            if (neuron_start && neuron_start_d1) begin
                $error("ERROR: neuron_start held for more than 1 cycle -- expected a single pulse");
            end
        end
    end

    //----------------------------------------------------
    // Watchdog 2: neuron_done must arrive within a bounded
    // window after neuron_start, or something downstream
    // (esn_neuron, its MAC, its tanh, or the BRAMs it reads)
    // is stalled. WAIT_CYCLES is generous -- one full neuron
    // pass is roughly (N_IN + N_RES) MAC iterations * a few
    // cycles each, plus tanh latency, so 2048 gives ample
    // margin without masking a real stall.
    //----------------------------------------------------
    localparam WAIT_CYCLES = 2048;

    integer wait_count;
    reg     waiting_for_done;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wait_count       <= 0;
            waiting_for_done <= 1'b0;
        end else begin
            if (state == WAIT_DONE) begin
                waiting_for_done <= 1'b1;
                if (waiting_for_done) begin
                    wait_count <= wait_count + 1;
                    if (wait_count == WAIT_CYCLES) begin
                        $error("ERROR: neuron_done not seen %0d cycles after neuron_start (neuron_idx=%0d) -- esn_neuron is stalled, check whether esn_neuron.start ever registered a 1, and whether its MAC/tanh handshake is completing",
                               WAIT_CYCLES, neuron_idx);
                    end
                end
            end else begin
                wait_count       <= 0;
                waiting_for_done <= 1'b0;
            end
        end
    end

`endif

endmodule
