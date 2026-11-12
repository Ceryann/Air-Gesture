"""Unduh hand_landmarker.task ke models/ (sekali saja; setelah itu 100% offline)."""
import sys
import urllib.request
from pathlib import Path

URL = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
       "hand_landmarker/float16/latest/hand_landmarker.task")
DEST = Path(__file__).resolve().parent.parent / "models" / "hand_landmarker.task"

if __name__ == "__main__":
    DEST.parent.mkdir(exist_ok=True)
    if DEST.exists():
        print(f"Sudah ada: {DEST}")
        sys.exit(0)
    print(f"Mengunduh {URL}\n -> {DEST}")
    urllib.request.urlretrieve(URL, DEST)
    print(f"Selesai ({DEST.stat().st_size / 1e6:.1f} MB)")
