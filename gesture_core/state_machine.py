"""State machine gestur -> perintah abstrak (ActionCommand).

Semua waktu `t` adalah detik (perf_counter) saat frame ditangkap, sehingga logika
deterministik dan bisa diuji tanpa kamera.

State Fase 0: IDLE, CURSOR_ACTIVE, CLICK_PENDING, SCROLL_ACTIVE, FROZEN.
(DRAG_ACTIVE dicadangkan untuk Fase 1.)
"""
from __future__ import annotations

import enum
import math
import threading
from typing import Optional

from .config import Config
from .types import FIST, NONE, OPEN_PALM, PINCH, SHAKA, TWO_FINGER, ActionCommand, GestureEvent


class State(enum.Enum):
    IDLE = "IDLE"
    CURSOR_ACTIVE = "CURSOR_ACTIVE"
    CLICK_PENDING = "CLICK_PENDING"
    SCROLL_ACTIVE = "SCROLL_ACTIVE"
    FROZEN = "FROZEN"


def _ms(t: float) -> int:
    return int(t * 1000)


class GestureStateMachine:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.state = State.IDLE
        # debouncer label
        self._stable = NONE
        self._stable_since = 0.0   # waktu capture frame PERTAMA dari label stabil saat ini
        self._cand: Optional[str] = None
        self._cand_n = 0
        self._cand_t0 = 0.0
        self._last_seen: Optional[float] = None
        # freeze
        self._shaka_t0: Optional[float] = None
        self._shaka_latched = False
        self._toggle_request = threading.Event()  # diset dari thread hotkey
        # klik / scroll
        self._click_t = -1e9
        self._scroll_anchor: Optional[float] = None
        self._scroll_prev_t = 0.0

    # ---- API ----
    def request_freeze_toggle(self) -> None:
        """Aman dipanggil dari thread lain (mis. hotkey)."""
        self._toggle_request.set()

    @property
    def stable_label(self) -> str:
        return self._stable

    def update(self, event: Optional[GestureEvent], t: float) -> list[ActionCommand]:
        cmds: list[ActionCommand] = []
        if self._toggle_request.is_set():
            self._toggle_request.clear()
            self._set_frozen(self.state != State.FROZEN, t, cmds)

        if event is None:
            if self._last_seen is not None and t - self._last_seen < self.cfg.lost_grace_s:
                return cmds  # tangan hilang sesaat: tahan keadaan
            self._force_stable(NONE, t)
        else:
            self._last_seen = t
            self._stabilize(event.label, t)

        self._update_freeze_gesture(t, cmds)
        if self.state == State.FROZEN:
            return cmds
        self._step(event, t, cmds)
        return cmds

    # ---- debouncer ----
    def _stabilize(self, raw: str, t: float) -> None:
        if raw == self._stable:
            self._cand, self._cand_n = None, 0
            return
        if raw != self._cand:
            self._cand, self._cand_n, self._cand_t0 = raw, 1, t
        else:
            self._cand_n += 1
        need = self.cfg.pinch_confirm_frames if raw == PINCH else self.cfg.confirm_frames
        if self._cand_n >= need:
            self._stable, self._stable_since = raw, self._cand_t0
            self._cand, self._cand_n = None, 0

    def _force_stable(self, label: str, t: float) -> None:
        if self._stable != label:
            self._stable, self._stable_since = label, t
        self._cand, self._cand_n = None, 0

    # ---- freeze ----
    def _update_freeze_gesture(self, t: float, cmds: list[ActionCommand]) -> None:
        if self._stable != SHAKA:
            self._shaka_t0, self._shaka_latched = None, False
            return
        if self._shaka_t0 is None:
            self._shaka_t0 = t
        if not self._shaka_latched and t - self._shaka_t0 >= self.cfg.freeze_hold_s:
            self._shaka_latched = True  # satu toggle per tahanan
            self._set_frozen(self.state != State.FROZEN, t, cmds)

    def _set_frozen(self, on: bool, t: float, cmds: list[ActionCommand]) -> None:
        self._reset_scroll()
        self.state = State.FROZEN if on else State.IDLE
        cmds.append(ActionCommand("freeze", {"on": on}, _ms(t)))

    # ---- transisi ----
    @staticmethod
    def _state_for(label: str) -> State:
        if label == OPEN_PALM:
            return State.CURSOR_ACTIVE
        if label == TWO_FINGER:
            return State.SCROLL_ACTIVE
        return State.IDLE

    def _enter(self, new: State, t: float, cmds: list[ActionCommand]) -> None:
        if new == self.state:
            return
        if new == State.CURSOR_ACTIVE:
            cmds.append(ActionCommand("reset_smoothing", {}, _ms(t)))  # PRD §10.6
        self._reset_scroll()
        self.state = new

    def _reset_scroll(self) -> None:
        self._scroll_anchor = None

    def _step(self, event: Optional[GestureEvent], t: float, cmds: list[ActionCommand]) -> None:
        lab, s = self._stable, self.state
        if s == State.IDLE:
            nxt = self._state_for(lab)
            if nxt != State.IDLE:  # pinch dari IDLE sengaja diabaikan (anti false-trigger)
                self._enter(nxt, t, cmds)
            return

        if s == State.CURSOR_ACTIVE:
            if lab == PINCH:
                self._click_t = t
                self.state = State.CLICK_PENDING
                cmds.append(ActionCommand(
                    "click", {"button": "left", "t_origin": self._stable_since}, _ms(t)))
            elif lab != OPEN_PALM:
                self._enter(self._state_for(lab), t, cmds)
            else:
                self._emit_cursor(event, t, cmds)
            return

        if s == State.CLICK_PENDING:
            # satu pinch = satu klik; harus dilepas dan lewat debounce
            if lab != PINCH and t - self._click_t >= self.cfg.click_debounce_s:
                self._enter(self._state_for(lab), t, cmds)
            return

        if s == State.SCROLL_ACTIVE:
            if lab != TWO_FINGER:
                self._enter(self._state_for(lab), t, cmds)
            else:
                self._emit_scroll(event, t, cmds)

    def _emit_cursor(self, event: Optional[GestureEvent], t: float, cmds: list[ActionCommand]) -> None:
        if event is None or t - self._click_t < self.cfg.post_click_lock_s:
            return
        if event.label == PINCH:  # pinch sedang terbentuk (belum stabil): jangan geser kursor
            return
        md = event.metadata
        cmds.append(ActionCommand("cursor_target", {"x": md["palm_x"], "y": md["palm_y"], "t": t}, _ms(t)))

    def _emit_scroll(self, event: Optional[GestureEvent], t: float, cmds: list[ActionCommand]) -> None:
        """Rate control: kecepatan scroll sebanding offset vertikal dari titik awal pose dua jari."""
        if event is None:
            return
        y = event.metadata["scroll_y"]
        if self._scroll_anchor is None:
            self._scroll_anchor, self._scroll_prev_t = y, t
            return
        dt = min(max(t - self._scroll_prev_t, 0.0), 0.1)
        self._scroll_prev_t = t
        off = self._scroll_anchor - y  # tangan naik => positif => scroll naik
        if self.cfg.scroll_invert:
            off = -off
        mag = abs(off) - self.cfg.scroll_deadzone
        if mag <= 0:
            return
        rate = min(mag * self.cfg.scroll_gain, self.cfg.scroll_max_rate)  # notch/detik
        cmds.append(ActionCommand("scroll", {"notches": math.copysign(rate * dt, off)}, _ms(t)))
