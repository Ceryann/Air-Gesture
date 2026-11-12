"""Antrean 'latest wins' (PRD §9.2: buffer tunggal, frame lama dibuang)."""
from __future__ import annotations

import queue
from typing import Any


def put_latest(q: "queue.Queue[Any]", item: Any) -> None:
    try:
        q.put_nowait(item)
    except queue.Full:
        try:
            q.get_nowait()
        except queue.Empty:
            pass
        try:
            q.put_nowait(item)
        except queue.Full:
            pass
