"""Titik masuk:  python -m gesture_core [--dry-run] [--no-preview] [--config profil.json]"""
from __future__ import annotations

import argparse
import dataclasses
import logging
import sys

from .backends import get_backend
from .config import Config
from .pipeline import Pipeline


def main() -> None:
    ap = argparse.ArgumentParser(prog="gesture_core", description="GestureInput Fase 0")
    ap.add_argument("--config", help="file JSON override konfigurasi")
    ap.add_argument("--dry-run", action="store_true", help="jangan menggerakkan mouse asli (sangat disarankan untuk uji pertama)")
    ap.add_argument("--no-preview", action="store_true", help="tanpa jendela debug (lebih akurat untuk ukur latensi)")
    ap.add_argument("--camera", type=int, help="indeks kamera")
    ap.add_argument("--model", help="path hand_landmarker.task")
    ap.add_argument("--selfcheck", action="store_true", help="verifikasi dependensi + model (tanpa kamera) lalu keluar")
    ap.add_argument("--print-config", action="store_true", help="cetak konfigurasi efektif lalu keluar")
    ap.add_argument("--log-level", default="INFO")
    args = ap.parse_args()

    logging.basicConfig(level=args.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    cfg = Config.from_json(args.config) if args.config else Config()
    if args.dry_run:
        cfg.backend = "dry-run"
    if args.no_preview:
        cfg.preview = False
    if args.camera is not None:
        cfg.camera_index = args.camera
    if args.model:
        cfg.model_path = args.model
    if args.selfcheck:
        from .selfcheck import run
        sys.exit(run(cfg))
    if args.print_config:
        for k, v in dataclasses.asdict(cfg).items():
            print(f"{k} = {v}")
        return

    Pipeline(cfg, get_backend(cfg.backend)).run()


if __name__ == "__main__":
    main()
