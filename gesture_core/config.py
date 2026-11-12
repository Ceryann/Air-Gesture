"""Konfigurasi. Semua ambang batas di sini perlu di-tuning dengan kamera/tangan nyata."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, fields
from pathlib import Path



def _resource_root() -> Path:
    """Folder proyek saat dev; sys._MEIPASS saat dibundel PyInstaller (model ikut di sana)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


_ROOT = _resource_root()


@dataclass
class Config:
    # --- capture ---
    camera_index: int = 0
    width: int = 640
    height: int = 480
    fps: int = 30
    fourcc: str = "MJPG"  # MJPG umumnya memberi 30 fps stabil di 640x480 pada webcam USB

    # --- inference ---
    model_path: str = str(_ROOT / "models" / "hand_landmarker.task")
    num_hands: int = 1  # PRD: 2. Fase 0 hanya butuh 1 (zoom dua tangan ditunda)
    min_hand_detection_confidence: float = 0.6
    min_hand_presence_confidence: float = 0.5
    min_tracking_confidence: float = 0.5

    # --- klasifikasi (rasio dinormalisasi terhadap ukuran tangan) ---
    ext_ratio: float = 1.4            # jari "terulur" jika jarak ujung-pergelangan / pangkal-pergelangan > ini
    thumb_ratio: float = 1.05
    pinch_on: float = 0.28            # jarak ujung ibu jari-telunjuk / ukuran tangan: masuk pinch
    pinch_off: float = 0.42           # keluar pinch (hysteresis)
    pinch_index_min_ratio: float = 1.0  # telunjuk tidak boleh tertekuk penuh (membedakan pinch dari kepalan)
    min_confidence: float = 0.8

    # --- state machine ---
    confirm_frames: int = 3           # frame berturut-turut sebelum label dianggap stabil
    pinch_confirm_frames: int = 2     # lebih sedikit untuk pinch (menjaga latensi)
    lost_grace_s: float = 0.2         # toleransi tangan hilang sesaat
    click_debounce_s: float = 0.15    # < jendela double-click 400 ms (lihat catatan README)
    post_click_lock_s: float = 0.4    # kursor dikunci setelah klik agar double-click tidak meleset
    freeze_hold_s: float = 2.0
    scroll_deadzone: float = 0.04     # offset vertikal (tinggi frame) dari titik awal yang diabaikan
    scroll_gain: float = 120.0        # notch/detik per satuan offset di luar deadzone
    scroll_max_rate: float = 30.0     # notch/detik maksimum
    scroll_invert: bool = False

    # --- kursor ---
    active_region: tuple = (0.2, 0.15, 0.8, 0.75)  # (x0, y0, x1, y1) frame -> seluruh layar
    one_euro_min_cutoff: float = 1.0
    one_euro_beta: float = 0.02       # dipakai pada koordinat PIKSEL layar (bukan ternormalisasi)
    one_euro_d_cutoff: float = 1.0
    filter_gap_reset_s: float = 0.25

    # --- runtime ---
    backend: str = "auto"             # auto | windows | dry-run
    preview: bool = True
    hotkey_freeze: str = "<ctrl>+<alt>+f"
    hotkey_quit: str = "<ctrl>+<alt>+q"

    @property
    def aspect(self) -> float:
        return self.width / self.height

    @classmethod
    def from_json(cls, path: str) -> "Config":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        unknown = set(data) - {f.name for f in fields(cls)}
        if unknown:
            raise ValueError(f"Kunci konfigurasi tidak dikenal: {sorted(unknown)}")
        if "active_region" in data:
            data["active_region"] = tuple(data["active_region"])
        return cls(**data)
