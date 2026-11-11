# esn_axi_ip register map (AXI4-Lite, 32-bit, byte offsets)

| Offset | Name | Access | Bits |
|---|---|---|---|
| 0x00 | ID | RO | `0x45534E31` ("ESN1") |
| 0x04 | CAPS | RO | [7:0] N_IN, [19:8] N_RES, [31:20] T_MAX |
| 0x08 | CTRL | RW | [0] START (self-clearing), [1] CLEAR (self-clearing; zeroes state, timestep, readout accumulators), [2] STREAM_EN |
| 0x0C | STATUS | RO | [0] busy, [1] stream FSM active, [2] MAC overflow seen (sticky, cleared by CLEAR), [3] too-dense row (fast core only: a row of W has more than K nonzeros; always 0 on the serial core) |
| 0x10 | IRQ_STAT | RW1C | [0] STEP_DONE, [1] SOH_DONE, [2] OVERFLOW |
| 0x14 | IRQ_EN | RW | same bits; `irq` = OR(IRQ_STAT & IRQ_EN) |
| 0x18 | TIMESTEP | RO | index of the next time step |
| 0x1C | CYCLES | RO | clock cycles start→done of the last step |
| 0x20 | SOC | RO | [15:0] SOC Q2.14, [21:16] step it belongs to |
| 0x24 | SOH | RO | [15:0] SOH Q2.14 (valid after the last step of a window) |
| 0x28 | MEM_SEL | RW | 0 Win, 1 W, 2 input, 3 bias, 4 readout SOC weights, 5 readout SOH weights |
| 0x2C | MEM_ADDR | RW | [AW-1:0] address, [31] auto-increment after each MEM_DATA write |
| 0x30 | MEM_DATA | WO | [17:0] word: Q6.10 (memories 0–3) or Q4.14 (4–5; address N_RES = offset c) |

Memory layouts: Win[neuron·N_IN + j], W[neuron·N_RES + k], input[step·N_IN + j], bias[neuron], readout w[0..N_RES-1], c at N_RES.

Sequence (register mode): load memories (idle only) → `CTRL.CLEAR` → for each step: write u(t) to memory 2 at `t·N_IN`, `CTRL.START`, wait `IRQ_STAT.STEP_DONE`, read `SOC`; after the last step read `SOH`.
Stream mode: `CTRL.STREAM_EN=1`; send u(t) on `s_axis` (N_IN × int16 little-endian lanes); results on `m_axis` (64-bit: [15:0] SOC, [21:16] step, [47:32] SOH, TLAST on the last step).
Arithmetic: x(t+1)=tanh(Win·u+W·x+b), Q6.10, MAC rounded `(Σ+512)>>>10`, clip ±5, 5121-entry tanh LUT; SOC = sat16(((Σw·x+2^9)>>>10)+c); SOH = sat16(((Σ_t Σw·x+2^(9+log2 T))>>>(10+log2 T))+c).
