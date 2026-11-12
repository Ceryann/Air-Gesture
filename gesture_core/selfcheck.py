"""Verifikasi tanpa kamera: impor dependensi, muat model, deteksi pada gambar kosong.

Dipakai CI untuk memastikan hasil bundle PyInstaller benar-benar berjalan
(data MediaPipe ikut terbundel, model ditemukan, backend OS bisa dibuat).
Teks sengaja ASCII agar aman di konsol Windows mana pun.
"""
from __future__ import annotations

import platform
import sys
from pathlib import Path

from .config import Config


def run(cfg: Config) -> int:
    ok = True

    def step(name: str) -> None:
        print(f"[selfcheck] {name} ...", flush=True)

    print(f"[selfcheck] python {sys.version.split()[0]} | {platform.platform()} | frozen={getattr(sys, 'frozen', False)}")
    try:
        step("numpy + opencv")
        import cv2
        import numpy as np
        print(f"            numpy {np.__version__}, opencv {cv2.__version__}")

        step("mediapipe")
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision
        print(f"            mediapipe {getattr(mp, '__version__', '?')}")

        step(f"model: {cfg.model_path}")
        if not Path(cfg.model_path).is_file():
            raise FileNotFoundError("model tidak ditemukan (jalankan scripts/download_model.py)")
        print(f"            {Path(cfg.model_path).stat().st_size / 1e6:.1f} MB")

        step("HandLandmarker (mode IMAGE, gambar kosong)")
        options = vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=cfg.model_path),
            running_mode=vision.RunningMode.IMAGE, num_hands=1)
        landmarker = vision.HandLandmarker.create_from_options(options)
        try:
            blank = np.zeros((cfg.height, cfg.width, 3), dtype=np.uint8)
            result = landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=blank))
            assert hasattr(result, "hand_landmarks")
            print(f"            tangan terdeteksi di gambar kosong: {len(result.hand_landmarks)} (harus 0)")
        finally:
            landmarker.close()

        step("pynput (hotkey; opsional)")
        try:
            from pynput import keyboard  # noqa: F401
            print("            ok")
        except Exception as exc:  # hotkey opsional -> hanya peringatan
            print(f"            PERINGATAN: pynput tidak bisa dimuat: {exc}")

        step("backend input OS")
        from .backends import get_backend
        backend = get_backend("auto")
        print(f"            {type(backend).__name__}, layar {backend.screen_size()}")
    except Exception as exc:
        ok = False
        print(f"[selfcheck] GAGAL: {type(exc).__name__}: {exc}", flush=True)

    print("[selfcheck] SELFCHECK OK" if ok else "[selfcheck] SELFCHECK GAGAL", flush=True)
    return 0 if ok else 1
