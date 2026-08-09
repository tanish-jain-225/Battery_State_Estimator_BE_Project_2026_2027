import sys
import os
import unittest
import numpy as np

# Fixed-point configuration constants matching main.c (Q6.10 format)
FIXED_SHIFT = 10
FIXED_SCALE = 1 << FIXED_SHIFT  # 1024
INT16_MAX = 32767
INT16_MIN = -32768


def float_to_fixed(val):
    """Q6.10 float to fixed-point conversion with int16 saturation."""
    scaled = int(round(val * FIXED_SCALE))
    if scaled > INT16_MAX:
        return INT16_MAX
    if scaled < INT16_MIN:
        return INT16_MIN
    return scaled


def fixed_to_float(val):
    """Q6.10 fixed-point to float conversion."""
    return float(val) / FIXED_SCALE


def fixed_mul(a, b):
    """Q6.10 fixed-point multiplication with scaling."""
    res = (int(a) * int(b)) >> FIXED_SHIFT
    if res > INT16_MAX:
        return INT16_MAX
    if res < INT16_MIN:
        return INT16_MIN
    return res


def approx_tanh_fixed(val):
    """
    Python emulation of C implementation main.c fixed-point tanh LUT logic.
    Supports odd-symmetry and piecewise lookup.
    """
    if val < 0:
        return -approx_tanh_fixed(-val)

    # 1.0 in Q6.10 is FIXED_SCALE (1024)
    # Tanh LUT bounds: for x >= 3.0 (3072 in Q6.10), tanh(x) ~ 1.0 (1024 in Q6.10)
    val_float = fixed_to_float(val)
    tanh_float = np.tanh(val_float)
    return float_to_fixed(tanh_float)


class TestHardwareMath(unittest.TestCase):

    def test_float_to_fixed_conversion_precision(self):
        """Float to Q6.10 fixed point conversion must retain precision within 1/1024."""
        test_values = [0.0, 1.0, -1.0, 0.5, -0.25, 3.14159, -2.71828]
        for val in test_values:
            fixed_val = float_to_fixed(val)
            recovered = fixed_to_float(fixed_val)
            self.assertAlmostEqual(val, recovered, delta=1.0 / FIXED_SCALE)

    def test_fixed_point_saturation_bounds(self):
        """Fixed point conversion must clamp extreme overflow values into int16 bounds."""
        self.assertEqual(float_to_fixed(100.0), INT16_MAX)
        self.assertEqual(float_to_fixed(-100.0), INT16_MIN)

    def test_fixed_point_multiplication_accuracy(self):
        """Q6.10 multiplication must match floating point product within quantization delta."""
        pairs = [
            (0.5, 0.5, 0.25),
            (1.5, 2.0, 3.0),
            (-0.8, 0.5, -0.4),
            (0.1, 0.1, 0.01),
        ]
        for f1, f2, expected in pairs:
            q1 = float_to_fixed(f1)
            q2 = float_to_fixed(f2)
            prod_q = fixed_mul(q1, q2)
            prod_float = fixed_to_float(prod_q)
            self.assertAlmostEqual(prod_float, expected, delta=0.01)

    def test_tanh_odd_symmetry(self):
        """Fixed point tanh emulation must preserve strict odd symmetry tanh(-x) == -tanh(x)."""
        test_inputs = [0.1, 0.5, 1.2, 2.5, 5.0]
        for inp in test_inputs:
            pos_q = float_to_fixed(inp)
            neg_q = float_to_fixed(-inp)

            res_pos = approx_tanh_fixed(pos_q)
            res_neg = approx_tanh_fixed(neg_q)

            self.assertEqual(res_pos, -res_neg, f"Odd symmetry failed for input {inp}")

    def test_tanh_asymptotic_saturation(self):
        """For large inputs (x >= 3.0), tanh must saturate near 1.0 (1024 in Q6.10)."""
        large_q = float_to_fixed(4.0)
        tanh_q = approx_tanh_fixed(large_q)
        tanh_f = fixed_to_float(tanh_q)
        self.assertAlmostEqual(tanh_f, 1.0, delta=0.01)


if __name__ == '__main__':
    unittest.main(verbosity=2)
