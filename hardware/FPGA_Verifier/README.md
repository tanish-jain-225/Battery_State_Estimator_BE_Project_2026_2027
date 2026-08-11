[← Back to README](../../README.md) · [← Back to Hardware](../hardware.md)

# FPGA-Based Q6.10 Echo State Network

## Current Status

A 100-neuron fixed-point Echo State Network has been implemented
in Verilog and verified using Vivado/XSim.

### Architecture

- Input dimension: 4
- Reservoir size: 100
- Fixed-point format: Q6.10
- Input-weight multiplication: Win · u
- Recurrent multiplication: W · x
- Bias addition
- Saturation/clipping
- Hardware tanh LUT
- Double-buffered reservoir state memory

## Verification

The RTL was compared against an independent Python golden
reference model.

Two recurrent passes were evaluated:

- Pass 1: x(0) → x(1)
- Pass 2: x(1) → x(2)

Total neuron updates:

200

Results:

| Stage | Matches |
|-------|---------|
| MAC | 200/200 |
| Bias | 200/200 |
| Sum | 200/200 |
| Tanh input | 200/200 |
| Tanh output | 200/200 |

All stages matched bit-exactly.

## Verification & Sequence Scope

The implementation verifies recurrent state updates across multi-step sequences ($x(0) \to x(1) \to x(2)$) with bit-exact numerical parity against the Python golden reference model. Sequence-level address generator logic and state continuity are fully verified. On-board Artix-7 A7100T synthesizer target deployment and physical UART HIL testing remain scheduled for the upcoming Phase 2/3 hardware milestones.


## Project Structure

```
ESN_Q6_10/
│
├── README.md
│
├── rtl/
│   ├── esn_top.v
│   ├── esn_neuron.v
│   ├── reservoir_controller.v
│   ├── address_generator.v
│   ├── mac_accum_q6_10.v
│   ├── mult_q6_10.v
│   └── tanh_lut.v
│
├── memory/
│   ├── win_bram.coe
│   ├── w_bram.coe
│   ├── bias.coe
│   ├── input_bram.coe
│   └── tanh.mem
│
├── testbench/
│   └── tb_esn_top.v
│
├── python/
│   ├── golden_model.py
│   └── compare_results.py
│
└── verification/
    ├── golden.csv
    ├── vivado_esn_results.csv
    └── verification_report.txt
```
