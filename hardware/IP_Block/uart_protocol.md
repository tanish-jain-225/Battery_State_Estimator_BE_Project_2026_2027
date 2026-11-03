# Platform UART protocol (115200 8N1, 80 MHz clock)

Frame (both directions): `0xA5 | cmd | len_lo | len_hi | payload[len] | chk`, `chk = (cmd+len_lo+len_hi+Σpayload) mod 256`.
A half-received frame is dropped after 50 ms without a byte. One reply per command; send the next command after the reply.

| Cmd | Name | Payload | Reply |
|---|---|---|---|
| 0x01 | WRITE | `target, wb, addr_lo, addr_hi, words…` (little-endian, `wb` bytes each, address auto-increments) | 0x81 `[status]` (0 ok, 1 bad checksum, 2 unknown command) |
| 0x02 | CTRL | `flags`: bit0 clear ESN state/timestep/readout, bit1 EKF init pulse | 0x81 `[status]` after the clear has finished |
| 0x03 | STEP | `u[0..N_IN-1]` int16 Q6.10, `I` int32 Q4.28, `Vmeas` int32 Q4.28 | 0x83, 21 bytes (below) |
| 0x04 | PING | – | 0x84 `'E','P',1,N_IN,N_RES lo/hi,T_MAX lo/hi` |

WRITE targets: 0 ESN Win · 1 W · 2 input · 3 bias (Q6.10, wb=2) · 4 readout SOC · 5 readout SOH (Q4.14 in 4 bytes, index N_RES = offset) · 8 EKF registers · 9 UKF registers (wb=4, word address = register index) · 10 EKF OCV · 11 EKF slope · 12 UKF OCV · 13 UKF slope (1024 entries, wb=4).
A WRITE with a bad checksum may already have written part of its data: resend the whole frame.

STEP reply payload: `[0]` step index · `[1]` flags (bit0 SOH valid, bit1 MAC overflow seen) · `[2:3]` ESN SOC Q2.14 · `[4:7]` EKF SOC Q2.30 · `[8:11]` UKF SOC Q2.30 · `[12:13]` ESN SOH Q2.14 · `[14:16]` ESN cycles · `[17:18]` EKF cycles · `[19:20]` UKF cycles (counted on the chip from the common start pulse to each done).
Per-window sequence: EKF/UKF constant writes -> CTRL(clear+init) -> 64 x STEP. EKF register indices: 0 SOC0, 22 a, 23 b, 24 kcc, 25 R0, 26 Q0, 27 Q1, 28 R, 31 P0; (I, V are written by STEP into 20/21). UKF indices from [`ukf_fixed.py`](ukf_fixed.py) (`REGS`).
