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

## Current Scope

The current implementation verifies recurrent state updates
using the same input vector across passes.
Multi-timestep sequence input addressing is the next development
stage.


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
