"""Wiring tiga thread (PRD §9.2): capture -> inference -> control loop (thread utama)."""
from __future__ import annotations

import logging
import queue
import threading
import time

from .backends import InputBackend
from .classifier import HeuristicClassifier
from .config import Config
from .cursor_mapper import CursorMapper
from .metrics import LatencyStats
from .state_machine import GestureStateMachine
from .types import ActionCommand, LandmarkFrame

log = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, cfg: Config, backend: InputBackend):
        self.cfg, self.backend = cfg, backend
        self.stop = threading.Event()
        self.frame_q: queue.Queue = queue.Queue(maxsize=1)
        self.landmark_q: queue.Queue = queue.Queue(maxsize=1)
        sw, sh = backend.screen_size()
        self.classifier = HeuristicClassifier(cfg)
        self.sm = GestureStateMachine(cfg)
        self.mapper = CursorMapper(cfg, sw, sh)
        self.stats = LatencyStats()
        self.last_event = None

    # ---- satu frame: klasifikasi -> state machine -> eksekusi ----
    def process(self, lf: LandmarkFrame) -> float:
        t0 = time.perf_counter()
        event = self.classifier.classify(lf.hands[0], lf.timestamp_ms) if lf.hands else None
        self.last_event = event
        t1 = time.perf_counter()
        cmds = self.sm.update(event, lf.t_capture)
        t2 = time.perf_counter()
        self._execute(cmds)
        t3 = time.perf_counter()

        total_ms = (t3 - lf.t_capture) * 1000
        if lf.t_landmarks:
            self.stats.record("capture->landmarks", (lf.t_landmarks - lf.t_capture) * 1000)
        self.stats.record("classify+state", (t2 - t0) * 1000)
        self.stats.record("execute", (t3 - t2) * 1000)
        self.stats.record("frame_total", total_ms)
        for c in cmds:
            if c.action == "click":  # latensi dari frame PERTAMA pinch (termasuk debounce)
                self.stats.record("pinch->click", (t3 - c.params["t_origin"]) * 1000)
        self.stats.tick()
        return total_ms

    def _execute(self, cmds: list[ActionCommand]) -> None:
        for c in cmds:
            a, p = c.action, c.params
            if a == "cursor_target":
                self.backend.move(*self.mapper.map(p["x"], p["y"], p["t"]))
            elif a == "reset_smoothing":
                self.mapper.reset()
            elif a == "click":
                self.backend.click(p["button"])
                log.info("CLICK")
            elif a == "scroll":
                self.backend.scroll(p["notches"])
            elif a == "freeze":
                log.warning("FREEZE %s", "AKTIF (input gestur dihentikan)" if p["on"] else "dilepas")

    # ---- siklus hidup ----
    def run(self) -> None:
        from .capture import CaptureThread
        from .inference import InferenceThread

        # InferenceThread dibuat di thread utama agar error model/mediapipe langsung terlihat.
        inf = InferenceThread(self.cfg, self.frame_q, self.landmark_q, self.stop)
        cap = CaptureThread(self.cfg, self.frame_q, self.stop)
        hotkeys = self._start_hotkeys()
        cap.start()
        inf.start()
        log.info("Berjalan. Freeze: %s | Keluar: %s%s", self.cfg.hotkey_freeze, self.cfg.hotkey_quit,
                 " | q/ESC di jendela preview" if self.cfg.preview else " | Ctrl+C")
        try:
            while not self.stop.is_set():
                try:
                    lf = self.landmark_q.get(timeout=0.1)
                except queue.Empty:
                    continue
                total_ms = self.process(lf)
                if self.cfg.preview and lf.frame_bgr is not None:
                    from .debug_view import draw
                    key = draw(lf, self.last_event, self.sm.state.value, self.sm.stable_label,
                               self.cfg, total_ms)
                    if key in (27, ord("q")):
                        break
        except KeyboardInterrupt:
            pass
        finally:
            self.stop.set()
            if hotkeys:
                hotkeys.stop()
            cap.join(timeout=1.0)
            inf.join(timeout=1.0)
            self.backend.close()
            if self.cfg.preview:
                import cv2
                cv2.destroyAllWindows()
            self.stats.report()
        if cap.error:
            raise RuntimeError(cap.error)

    def _start_hotkeys(self):
        try:
            from pynput import keyboard
        except Exception as exc:  # pragma: no cover
            log.warning("pynput tidak tersedia, hotkey nonaktif: %s", exc)
            return None
        hk = keyboard.GlobalHotKeys({
            self.cfg.hotkey_freeze: self.sm.request_freeze_toggle,
            self.cfg.hotkey_quit: self.stop.set,
        })
        hk.start()
        return hk
