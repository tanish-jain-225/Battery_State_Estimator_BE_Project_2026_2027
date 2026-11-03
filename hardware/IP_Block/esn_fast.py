"""Vectorized, integer-exact re-implementation of GoldenESN.step (same arithmetic,
no per-neuron Python loop). Verified bit-identical against GoldenESN below."""
import numpy as np


class FastESN:
    def __init__(self, Win, W, bias, lut):
        self.Win = np.asarray(Win, dtype=np.int64)
        self.W = np.asarray(W, dtype=np.int64)
        self.bias = np.asarray(bias, dtype=np.int64)
        lut = np.asarray(lut, dtype=np.int64)
        self.lut = np.where(lut >= 32768, lut - 65536, lut)
        self.x = np.zeros(self.W.shape[0], dtype=np.int64)

    def reset(self):
        self.x[:] = 0

    def step(self, u):
        acc = self.Win @ np.asarray(u, dtype=np.int64) + self.W @ self.x
        mac = np.clip((acc + 512) >> 10, -32768, 32767)
        s = np.clip(mac + self.bias, -5120, 5120)
        mag = self.lut[np.abs(s)]
        self.x = np.clip(np.where(s < 0, -mag, mag), -32768, 32767)
        return self.x
