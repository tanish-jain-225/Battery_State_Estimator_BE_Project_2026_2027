/* esn_ip.h -- bare-metal driver for the ESN AXI IP (MicroBlaze / Zynq PS / any AXI master)
 * Register map: see docs/register_map.md.  Q6.10 = int16 with 10 fractional bits.
 */
#ifndef ESN_IP_H
#define ESN_IP_H
#include <stdint.h>

#define ESN_ID          0x00u
#define ESN_CAPS        0x04u
#define ESN_CTRL        0x08u
#define ESN_STATUS      0x0Cu
#define ESN_IRQ_STAT    0x10u
#define ESN_IRQ_EN      0x14u
#define ESN_TIMESTEP    0x18u
#define ESN_CYCLES      0x1Cu
#define ESN_SOC         0x20u
#define ESN_SOH         0x24u
#define ESN_MEM_SEL     0x28u
#define ESN_MEM_ADDR    0x2Cu
#define ESN_MEM_DATA    0x30u

#define ESN_CTRL_START      (1u << 0)
#define ESN_CTRL_CLEAR      (1u << 1)
#define ESN_CTRL_STREAM_EN  (1u << 2)
#define ESN_IRQ_STEP_DONE   (1u << 0)
#define ESN_IRQ_SOH_DONE    (1u << 1)
#define ESN_IRQ_OVERFLOW    (1u << 2)
#define ESN_MEM_WIN   0u
#define ESN_MEM_W     1u
#define ESN_MEM_INPUT 2u
#define ESN_MEM_BIAS  3u
#define ESN_MEM_RO_SOC 4u
#define ESN_MEM_RO_SOH 5u
#define ESN_ADDR_AUTOINC (1u << 31)

typedef struct { volatile uint32_t *base; } esn_t;

static inline void     esn_wr(esn_t *e, uint32_t off, uint32_t v) { e->base[off >> 2] = v; }
static inline uint32_t esn_rd(esn_t *e, uint32_t off)             { return e->base[off >> 2]; }

static inline int esn_present(esn_t *e) { return esn_rd(e, ESN_ID) == 0x45534E31u; }

/* load n 16/18-bit words into memory `sel` starting at address 0 */
static inline void esn_load(esn_t *e, uint32_t sel, const int32_t *data, uint32_t n)
{
    esn_wr(e, ESN_MEM_SEL, sel);
    esn_wr(e, ESN_MEM_ADDR, ESN_ADDR_AUTOINC);
    for (uint32_t i = 0; i < n; i++) esn_wr(e, ESN_MEM_DATA, (uint32_t)data[i] & 0x3FFFFu);
}

static inline void esn_clear(esn_t *e)
{
    esn_wr(e, ESN_CTRL, ESN_CTRL_CLEAR);
    while (esn_rd(e, ESN_STATUS) & 1u) { }
}

/* run one time step; the step's inputs must already be in memory ESN_MEM_INPUT.
 * returns SOC in Q2.14 (divide by 16384.0 for 0..1) */
static inline int16_t esn_step(esn_t *e)
{
    esn_wr(e, ESN_IRQ_STAT, ESN_IRQ_STEP_DONE);
    esn_wr(e, ESN_CTRL, ESN_CTRL_START);
    while (!(esn_rd(e, ESN_IRQ_STAT) & ESN_IRQ_STEP_DONE)) { }
    return (int16_t)(esn_rd(e, ESN_SOC) & 0xFFFFu);
}

/* SOH of the finished window, Q2.14 */
static inline int16_t esn_soh(esn_t *e) { return (int16_t)(esn_rd(e, ESN_SOH) & 0xFFFFu); }

#endif
