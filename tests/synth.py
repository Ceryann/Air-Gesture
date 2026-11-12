"""Generator landmark tangan sintetis (tangan menghadap kamera, jari ke atas, y ke bawah)."""
import numpy as np

from gesture_core.types import GestureEvent, HandLandmarks

_MCP_X = {"index": 0.44, "middle": 0.50, "ring": 0.56, "pinky": 0.61}
_IDX = {"index": 5, "middle": 9, "ring": 13, "pinky": 17}


def make_hand(index=True, middle=True, ring=True, pinky=True, thumb=True, pinch=False,
              dx=0.0, dy=0.0) -> HandLandmarks:
    pts = np.zeros((21, 3), dtype=np.float32)
    pts[0] = (0.50, 0.80, 0)                      # pergelangan
    pts[1], pts[2], pts[3] = (0.45, 0.75, 0), (0.40, 0.70, 0), (0.36, 0.66, 0)
    pts[4] = (0.30, 0.62, 0) if thumb else (0.47, 0.62, 0)
    ext = {"index": index, "middle": middle, "ring": ring, "pinky": pinky}
    for name, base in _IDX.items():
        x, y = _MCP_X[name], 0.60
        pts[base] = (x, y, 0)
        if ext[name]:
            pts[base + 1], pts[base + 2], pts[base + 3] = (x, y - 0.07, 0), (x, y - 0.12, 0), (x, y - 0.16, 0)
        else:
            pts[base + 1], pts[base + 2], pts[base + 3] = (x, y - 0.06, 0), (x, y - 0.02, 0), (x, y + 0.04, 0)
    if pinch:
        pts[4] = pts[8] + np.array([-0.02, 0.01, 0], dtype=np.float32)
    pts[:, 0] += dx
    pts[:, 1] += dy
    return HandLandmarks(points=pts, confidence=0.95)


def ev(label, palm=(0.5, 0.5), scroll_y=0.4, t=0.0, raw=None) -> GestureEvent:
    return GestureEvent(int(t * 1000), label, 1.0, "0",
                        {"palm_x": palm[0], "palm_y": palm[1], "scroll_y": scroll_y})
