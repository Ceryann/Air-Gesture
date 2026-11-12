"""Klasifikasi gestur statis berbasis heuristik geometri landmark (tanpa ML).

Semua ukuran dinormalisasi terhadap ukuran tangan (jarak pergelangan -> pangkal jari tengah),
dan jarak dihitung rotasi-invarian (jarak ke pergelangan, bukan sumbu Y) agar tangan
yang miring tetap terbaca.

Catatan: two_finger diperlakukan sebagai POSE di sini; gerakannya (naik/turun) dibaca
oleh state machine. Classifier ML (PRD §10.4) baru dibutuhkan di Fase 1+.
"""
from __future__ import annotations

import numpy as np

from .config import Config
from .types import FIST, NONE, OPEN_PALM, PINCH, SHAKA, TWO_FINGER, GestureEvent, HandLandmarks

WRIST = 0
THUMB_IP, THUMB_TIP = 3, 4
INDEX_MCP, INDEX_TIP = 5, 8
MIDDLE_MCP, MIDDLE_TIP = 9, 12
RING_MCP, RING_TIP = 13, 16
PINKY_MCP, PINKY_TIP = 17, 20

_FINGERS = {
    "index": (INDEX_MCP, INDEX_TIP),
    "middle": (MIDDLE_MCP, MIDDLE_TIP),
    "ring": (RING_MCP, RING_TIP),
    "pinky": (PINKY_MCP, PINKY_TIP),
}


class HeuristicClassifier:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._pinching: dict[str, bool] = {}

    def classify(self, hand: HandLandmarks, timestamp_ms: int, hand_id: str = "0") -> GestureEvent:
        cfg = self.cfg
        pts = hand.points
        p = pts[:, :2].astype(np.float64) * np.array([cfg.aspect, 1.0])  # koreksi rasio aspek

        def d(a: int, b: int) -> float:
            return float(np.linalg.norm(p[a] - p[b]))

        scale = max(d(WRIST, MIDDLE_MCP), 1e-6)
        ratios = {n: d(tip, WRIST) / max(d(mcp, WRIST), 1e-6) for n, (mcp, tip) in _FINGERS.items()}
        ext = {n: r > cfg.ext_ratio for n, r in ratios.items()}
        margin = {
            n: ((r - cfg.ext_ratio) if ext[n] else (cfg.ext_ratio - r)) / cfg.ext_ratio
            for n, r in ratios.items()
        }
        thumb_r = d(THUMB_TIP, PINKY_MCP) / max(d(THUMB_IP, PINKY_MCP), 1e-6)
        thumb_ext = thumb_r > cfg.thumb_ratio
        thumb_margin = abs(thumb_r - cfg.thumb_ratio) / cfg.thumb_ratio

        # --- pinch (dengan hysteresis) ---
        pinch_ratio = d(THUMB_TIP, INDEX_TIP) / scale
        limit = cfg.pinch_off if self._pinching.get(hand_id, False) else cfg.pinch_on
        is_pinch = pinch_ratio < limit and ratios["index"] > cfg.pinch_index_min_ratio
        self._pinching[hand_id] = is_pinch

        def conf(m: float) -> float:
            return float(np.clip(0.5 + 5.0 * m, 0.0, 1.0))

        label, confidence = NONE, 0.0
        n_ext = sum(ext.values())
        if is_pinch:
            label, confidence = PINCH, 1.0
        elif n_ext == 4:
            label, confidence = OPEN_PALM, conf(min(margin.values()))
        elif ext["index"] and ext["middle"] and not ext["ring"] and not ext["pinky"]:
            label, confidence = TWO_FINGER, conf(min(margin.values()))
        elif n_ext == 0:
            label, confidence = FIST, conf(min(margin.values()))
        elif ext["pinky"] and thumb_ext and not (ext["index"] or ext["middle"] or ext["ring"]):
            label, confidence = SHAKA, conf(min(min(margin.values()), thumb_margin))

        raw_label = label
        if confidence < cfg.min_confidence:
            label = NONE

        palm = pts[[WRIST, INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP], :2].mean(axis=0)
        return GestureEvent(
            timestamp_ms=timestamp_ms,
            label=label,
            confidence=confidence,
            hand_id=hand_id,
            metadata={
                "palm_x": float(palm[0]),
                "palm_y": float(palm[1]),
                "scroll_y": float((pts[INDEX_TIP, 1] + pts[MIDDLE_TIP, 1]) / 2.0),
                "pinch_ratio": pinch_ratio,
                "finger_ratios": ratios,
                "thumb_ratio": thumb_r,
                "raw_label": raw_label,
            },
        )
