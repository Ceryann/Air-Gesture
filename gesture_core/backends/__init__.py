"""Abstraksi injeksi input OS (PRD §10.7). Port macOS = implementasi InputBackend baru."""
from __future__ import annotations

import logging
import sys
from abc import ABC, abstractmethod

log = logging.getLogger(__name__)


class InputBackend(ABC):
    @abstractmethod
    def screen_size(self) -> tuple[int, int]: ...
    @abstractmethod
    def move(self, x: int, y: int) -> None: ...
    @abstractmethod
    def click(self, button: str = "left") -> None: ...
    @abstractmethod
    def scroll(self, notches: float) -> None:
        """notches > 0 = scroll naik. 1.0 = satu 'klik' roda mouse."""
    def close(self) -> None:
        pass


class DryRunBackend(InputBackend):
    """Tidak menyentuh OS: hanya mencatat. Aman untuk uji pertama & untuk non-Windows."""

    def __init__(self, size: tuple[int, int] = (1920, 1080)):
        self._size = size
        self.calls: list[tuple] = []

    def screen_size(self): return self._size
    def move(self, x, y): self.calls.append(("move", x, y))
    def click(self, button="left"):
        self.calls.append(("click", button)); log.info("[dry-run] CLICK %s", button)
    def scroll(self, notches):
        self.calls.append(("scroll", notches)); log.debug("[dry-run] scroll %.2f", notches)


def get_backend(name: str = "auto") -> InputBackend:
    if name == "dry-run":
        return DryRunBackend()
    if name in ("auto", "windows"):
        if sys.platform == "win32":
            from .windows import WindowsBackend
            return WindowsBackend()
        if name == "windows":
            raise RuntimeError("Backend 'windows' hanya untuk Windows.")
        log.warning("Bukan Windows: memakai backend dry-run (macOS = Fase 3).")
        return DryRunBackend()
    raise ValueError(f"Backend tidak dikenal: {name}")
