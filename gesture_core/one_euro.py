"""One Euro Filter (Casiez et al., 2012). Waktu dalam detik."""
from __future__ import annotations

import math


def _alpha(cutoff: float, dt: float) -> float:
    tau = 1.0 / (2.0 * math.pi * cutoff)
    return 1.0 / (1.0 + tau / dt)


class OneEuroFilter:
    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.02, d_cutoff: float = 1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.reset()

    def reset(self) -> None:
        self._x_hat: float | None = None
        self._dx_hat = 0.0
        self._x_prev: float | None = None
        self._t_prev: float | None = None

    def __call__(self, x: float, t: float) -> float:
        if self._x_hat is None:
            self._x_hat, self._x_prev, self._t_prev = x, x, t
            return x
        dt = max(t - self._t_prev, 1e-6)
        dx = (x - self._x_prev) / dt
        a_d = _alpha(self.d_cutoff, dt)
        self._dx_hat = a_d * dx + (1.0 - a_d) * self._dx_hat
        cutoff = self.min_cutoff + self.beta * abs(self._dx_hat)
        a = _alpha(cutoff, dt)
        self._x_hat = a * x + (1.0 - a) * self._x_hat
        self._x_prev, self._t_prev = x, t
        return self._x_hat
