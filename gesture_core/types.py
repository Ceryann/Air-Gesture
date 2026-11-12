"""Kontrak antarmuka inti (PRD §15) + field tambahan untuk latensi/debug."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

# Label gestur
OPEN_PALM = "open_palm"
PINCH = "pinch"
TWO_FINGER = "two_finger"
FIST = "fist"
SHAKA = "shaka"  # ibu jari + kelingking: gestur freeze (menggantikan "telapak tertutup")
NONE = "none"


@dataclass
class HandLandmarks:
    points: np.ndarray  # (21, 3), koordinat ternormalisasi gambar (x kanan, y bawah)
    confidence: float


@dataclass
class LandmarkFrame:
    timestamp_ms: int
    hands: list[HandLandmarks]
    handedness: list[str]
    # --- tambahan (bukan bagian kontrak PRD) ---
    t_capture: float = 0.0          # perf_counter() saat frame dibaca dari kamera
    t_landmarks: float = 0.0        # perf_counter() saat hasil MediaPipe tiba
    frame_bgr: Optional[np.ndarray] = None  # hanya untuk preview debug


@dataclass
class GestureEvent:
    timestamp_ms: int
    label: str
    confidence: float
    hand_id: str
    metadata: dict = field(default_factory=dict)


@dataclass
class ActionCommand:
    action: str
    params: dict
    timestamp_ms: int
