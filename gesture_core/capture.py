"""Thread 1: capture kamera. Frame di-flip (cermin) dan ditaruh di buffer tunggal."""
from __future__ import annotations

import logging
import queue
import sys
import threading
import time
from dataclasses import dataclass

import cv2
import numpy as np

from .config import Config
from .queues import put_latest

log = logging.getLogger(__name__)


@dataclass
class CapturedFrame:
    frame_bgr: np.ndarray
    t_capture: float  # perf_counter() tepat setelah read() kembali


class CaptureThread(threading.Thread):
    def __init__(self, cfg: Config, out_q: "queue.Queue[CapturedFrame]", stop: threading.Event):
        super().__init__(name="capture", daemon=True)
        self.cfg, self.out_q, self.stop_evt = cfg, out_q, stop
        self.error: str | None = None

    def run(self) -> None:
        cfg = self.cfg
        api = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
        cap = cv2.VideoCapture(cfg.camera_index, api)
        if not cap.isOpened():
            self.error = f"Kamera {cfg.camera_index} tidak bisa dibuka."
            self.stop_evt.set()
            return
        if cfg.fourcc:
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*cfg.fourcc))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.height)
        cap.set(cv2.CAP_PROP_FPS, cfg.fps)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # tidak semua backend menghormati ini
        log.info("Kamera: %dx%d @ %.0f fps", cap.get(cv2.CAP_PROP_FRAME_WIDTH),
                 cap.get(cv2.CAP_PROP_FRAME_HEIGHT), cap.get(cv2.CAP_PROP_FPS))
        fails = 0
        try:
            while not self.stop_evt.is_set():
                ok, frame = cap.read()
                t = time.perf_counter()
                if not ok:
                    fails += 1
                    if fails > 30:
                        self.error = "Kamera berhenti mengirim frame."
                        self.stop_evt.set()
                        break
                    time.sleep(0.01)
                    continue
                fails = 0
                put_latest(self.out_q, CapturedFrame(cv2.flip(frame, 1), t))
        finally:
            cap.release()
