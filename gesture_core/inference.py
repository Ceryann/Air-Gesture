"""Thread 2: MediaPipe HandLandmarker (LIVE_STREAM + detect_async)."""
from __future__ import annotations

import logging
import queue
import threading
import time
from pathlib import Path

import cv2
import numpy as np

from .capture import CapturedFrame
from .config import Config
from .queues import put_latest
from .types import HandLandmarks, LandmarkFrame

log = logging.getLogger(__name__)
MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
             "hand_landmarker/float16/latest/hand_landmarker.task")


class InferenceThread(threading.Thread):
    def __init__(self, cfg: Config, in_q: "queue.Queue[CapturedFrame]",
                 out_q: "queue.Queue[LandmarkFrame]", stop: threading.Event):
        super().__init__(name="inference", daemon=True)
        self.cfg, self.in_q, self.out_q, self.stop_evt = cfg, in_q, out_q, stop
        self._pending: dict[int, CapturedFrame] = {}
        self._lock = threading.Lock()

        if not Path(cfg.model_path).is_file():
            raise FileNotFoundError(
                f"Model tidak ditemukan: {cfg.model_path}\n"
                f"Jalankan: python scripts/download_model.py   (atau unduh dari {MODEL_URL})")
        import mediapipe as mp  # impor lambat agar modul lain bisa diuji tanpa mediapipe
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        self._mp = mp
        options = vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=cfg.model_path),
            running_mode=vision.RunningMode.LIVE_STREAM,
            num_hands=cfg.num_hands,
            min_hand_detection_confidence=cfg.min_hand_detection_confidence,
            min_hand_presence_confidence=cfg.min_hand_presence_confidence,
            min_tracking_confidence=cfg.min_tracking_confidence,
            result_callback=self._on_result,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)

    # Dipanggil dari thread internal MediaPipe. Frame yang diabaikan karena detektor sibuk
    # tidak pernah memanggil callback -> entri _pending dipangkas di run().
    def _on_result(self, result, output_image, timestamp_ms: int) -> None:
        t_now = time.perf_counter()
        with self._lock:
            cap = self._pending.pop(timestamp_ms, None)
        if cap is None:
            return
        hands, handed = [], []
        for i, lms in enumerate(result.hand_landmarks):
            pts = np.array([[lm.x, lm.y, lm.z] for lm in lms], dtype=np.float32)
            cat = result.handedness[i][0]
            hands.append(HandLandmarks(points=pts, confidence=float(cat.score)))
            handed.append(cat.category_name)
        put_latest(self.out_q, LandmarkFrame(
            timestamp_ms=timestamp_ms, hands=hands, handedness=handed,
            t_capture=cap.t_capture, t_landmarks=t_now,
            frame_bgr=cap.frame_bgr if self.cfg.preview else None))

    def run(self) -> None:
        last_ts = -1
        try:
            while not self.stop_evt.is_set():
                try:
                    cf = self.in_q.get(timeout=0.1)
                except queue.Empty:
                    continue
                ts = max(int(cf.t_capture * 1000), last_ts + 1)  # wajib naik-monoton (ms)
                last_ts = ts
                rgb = cv2.cvtColor(cf.frame_bgr, cv2.COLOR_BGR2RGB)
                image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
                with self._lock:
                    self._pending[ts] = cf
                    if len(self._pending) > 8:
                        for k in sorted(self._pending)[:-8]:
                            del self._pending[k]
                self._landmarker.detect_async(image, ts)
        finally:
            self._landmarker.close()
