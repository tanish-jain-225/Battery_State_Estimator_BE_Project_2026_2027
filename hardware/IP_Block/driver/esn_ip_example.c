/* Example: run the 64-step window of NASA B0018 cycle 115 on the ESN IP.
 * ESN_BASE is the AXI address given in the Vivado address editor.                        */
#include "esn_ip.h"
#include <stdio.h>
#define ESN_BASE 0x44A00000u
extern const int32_t win[400], w[10000], bias[100], ro_soc[101], ro_soh[101], u[64 * 4];

int main(void)
{
    esn_t e = { (volatile uint32_t *)ESN_BASE };
    if (!esn_present(&e)) { printf("ESN IP not found\n"); return 1; }
    esn_load(&e, ESN_MEM_WIN, win, 400);   esn_load(&e, ESN_MEM_W, w, 10000);
    esn_load(&e, ESN_MEM_BIAS, bias, 100);
    esn_load(&e, ESN_MEM_RO_SOC, ro_soc, 101);  esn_load(&e, ESN_MEM_RO_SOH, ro_soh, 101);
    esn_load(&e, ESN_MEM_INPUT, u, 256);
    esn_clear(&e);
    for (int t = 0; t < 64; t++) printf("step %2d SOC %.4f\n", t, esn_step(&e) / 16384.0);
    printf("SOH %.4f, last step %u cycles\n", esn_soh(&e) / 16384.0, esn_rd(&e, ESN_CYCLES));
    return 0;
}
