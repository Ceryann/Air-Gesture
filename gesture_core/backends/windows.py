"""Backend Windows murni ctypes (tanpa pynput untuk output -> latensi rendah, dependensi sedikit).

SetCursorPos untuk gerak kursor, mouse_event untuk klik/scroll. mouse_event secara resmi
'superseded' oleh SendInput namun masih didukung penuh; cukup untuk PoC. Ganti ke SendInput
di Fase 1 bila butuh integritas lebih (mis. UIPI / aplikasi elevated).
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes

from . import InputBackend

_user32 = ctypes.windll.user32
_LEFTDOWN, _LEFTUP, _RIGHTDOWN, _RIGHTUP, _WHEEL = 0x0002, 0x0004, 0x0008, 0x0010, 0x0800
_WHEEL_DELTA = 120


class WindowsBackend(InputBackend):
    def __init__(self) -> None:
        # Tanpa ini Windows menskalakan koordinat pada layar DPI tinggi (kursor 'meleset').
        try:
            _user32.SetProcessDPIAware()
        except Exception:
            pass
        self._w = _user32.GetSystemMetrics(0)  # monitor utama saja (MVP)
        self._h = _user32.GetSystemMetrics(1)
        _user32.mouse_event.argtypes = [
            wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]
        _user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]

    def screen_size(self) -> tuple[int, int]:
        return self._w, self._h

    def move(self, x: int, y: int) -> None:
        _user32.SetCursorPos(max(0, min(int(x), self._w - 1)), max(0, min(int(y), self._h - 1)))

    def click(self, button: str = "left") -> None:
        down, up = (_LEFTDOWN, _LEFTUP) if button == "left" else (_RIGHTDOWN, _RIGHTUP)
        _user32.mouse_event(down, 0, 0, 0, 0)
        _user32.mouse_event(up, 0, 0, 0, 0)

    def scroll(self, notches: float) -> None:
        delta = int(round(notches * _WHEEL_DELTA))  # roda resolusi-tinggi: delta < 120 diperbolehkan
        if delta:
            _user32.mouse_event(_WHEEL, 0, 0, delta & 0xFFFFFFFF, 0)
