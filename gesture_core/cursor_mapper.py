"""Peta koordinat tangan (ternormalisasi) -> piksel layar, lalu One Euro Filter di ruang piksel."""
from __future__ import annotations

from .config import Config
from .one_euro import OneEuroFilter


class CursorMapper:
    def __init__(self, cfg: Config, screen_w: int, screen_h: int):
        self.cfg = cfg
        self.sw, self.sh = screen_w, screen_h
        self._fx = OneEuroFilter(cfg.one_euro_min_cutoff, cfg.one_euro_beta, cfg.one_euro_d_cutoff)
        self._fy = OneEuroFilter(cfg.one_euro_min_cutoff, cfg.one_euro_beta, cfg.one_euro_d_cutoff)
        self._last_t: float | None = None

    def reset(self) -> None:
        self._fx.reset()
        self._fy.reset()
        self._last_t = None

    def map(self, nx: float, ny: float, t: float) -> tuple[int, int]:
        x0, y0, x1, y1 = self.cfg.active_region
        u = min(max((nx - x0) / (x1 - x0), 0.0), 1.0)
        v = min(max((ny - y0) / (y1 - y0), 0.0), 1.0)
        px, py = u * (self.sw - 1), v * (self.sh - 1)
        if self._last_t is not None and t - self._last_t > self.cfg.filter_gap_reset_s:
            self.reset()
        self._last_t = t
        return int(round(self._fx(px, t))), int(round(self._fy(py, t)))
