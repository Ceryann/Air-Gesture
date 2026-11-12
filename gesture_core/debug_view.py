"""Jendela preview debug: skeleton tangan, region aktif, label & rasio untuk tuning."""
from __future__ import annotations

import cv2

from .config import Config
from .types import GestureEvent, LandmarkFrame

_CONN = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11),
         (11, 12), (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (17, 18), (18, 19), (19, 20), (0, 17)]


def draw(lf: LandmarkFrame, event: GestureEvent | None, state: str, stable: str,
         cfg: Config, total_ms: float):
    img = lf.frame_bgr
    h, w = img.shape[:2]
    x0, y0, x1, y1 = cfg.active_region
    cv2.rectangle(img, (int(x0 * w), int(y0 * h)), (int(x1 * w), int(y1 * h)), (0, 160, 0), 1)
    for hand in lf.hands:
        px = [(int(x * w), int(y * h)) for x, y, _ in hand.points]
        for a, b in _CONN:
            cv2.line(img, px[a], px[b], (255, 200, 0), 1)
        for p in px:
            cv2.circle(img, p, 3, (0, 0, 255), -1)
    frozen = state == "FROZEN"
    lines = [f"STATE: {state}", f"stable: {stable}  | {total_ms:5.1f} ms"]
    if event is not None:
        md = event.metadata
        fr = md["finger_ratios"]
        lines += [f"raw: {md['raw_label']} -> {event.label} ({event.confidence:.2f})",
                  f"pinch={md['pinch_ratio']:.2f}  thumb={md['thumb_ratio']:.2f}",
                  "ext i/m/r/p: " + " ".join(f"{fr[k]:.2f}" for k in ("index", "middle", "ring", "pinky"))]
    for i, text in enumerate(lines):
        cv2.putText(img, text, (8, 20 + 18 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 0, 255) if frozen else (0, 255, 0), 1, cv2.LINE_AA)
    if frozen:
        cv2.putText(img, "FROZEN", (w // 2 - 70, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                    (0, 0, 255), 2, cv2.LINE_AA)
    cv2.imshow("GestureInput - debug (q/ESC = keluar)", img)
    return cv2.waitKey(1) & 0xFF
