"""Agregasi latensi p50/p95/p99 per N frame (PRD §10.10)."""
from __future__ import annotations

import logging
from collections import defaultdict

import numpy as np

log = logging.getLogger("gesture_core.latency")


class LatencyStats:
    def __init__(self, window: int = 100):
        self.window = window
        self._buf: dict[str, list[float]] = defaultdict(list)
        self._frames = 0
        self.last_total_ms = 0.0

    def record(self, name: str, ms: float) -> None:
        self._buf[name].append(ms)

    def tick(self) -> None:
        self._frames += 1
        if self._frames % self.window == 0:
            self.report()

    def report(self) -> None:
        parts = []
        for name, vals in self._buf.items():
            if vals:
                p50, p95, p99 = np.percentile(vals, [50, 95, 99])
                parts.append(f"{name}: p50={p50:.1f} p95={p95:.1f} p99={p99:.1f} (n={len(vals)})")
        if parts:
            log.info(" | ".join(parts) + "  [ms]")
        self._buf.clear()
