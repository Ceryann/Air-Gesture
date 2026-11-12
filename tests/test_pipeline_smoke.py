"""Smoke test pipeline end-to-end tanpa kamera/MediaPipe: landmark sintetis -> backend dry-run."""
import unittest

from gesture_core.backends import DryRunBackend
from gesture_core.config import Config
from gesture_core.pipeline import Pipeline
from gesture_core.types import LandmarkFrame
from tests.synth import make_hand


class PipelineSmoke(unittest.TestCase):
    def feed(self, p, hand, n, t0):
        for i in range(n):
            t = t0 + i / 30
            hands = [hand] if hand is not None else []
            p.process(LandmarkFrame(int(t * 1000), hands, ["Right"] * len(hands), t_capture=t, t_landmarks=t))
        return t0 + n / 30

    def test_cursor_click_scroll_freeze(self):
        be = DryRunBackend((1920, 1080))
        p = Pipeline(Config(preview=False), be)
        t = 100.0
        t = self.feed(p, make_hand(dx=0.0), 8, t)                       # telapak: kursor
        moves = [c for c in be.calls if c[0] == "move"]
        self.assertTrue(moves)
        t = self.feed(p, make_hand(pinch=True), 8, t)                   # pinch: satu klik
        self.assertEqual(sum(c[0] == "click" for c in be.calls), 1)
        t = self.feed(p, make_hand(), 20, t)
        # dua jari, lalu angkat 0.12 tinggi frame -> scroll positif
        t = self.feed(p, make_hand(True, True, False, False, thumb=False), 8, t)
        n0 = len(be.calls)
        t = self.feed(p, make_hand(True, True, False, False, thumb=False, dy=-0.12), 15, t)
        sc = [c for c in be.calls[n0:] if c[0] == "scroll"]
        self.assertTrue(sc and all(c[1] > 0 for c in sc))
        # freeze via shaka 2.2 s
        t = self.feed(p, make_hand(False, False, False, True, thumb=True), 70, t)
        n1 = len(be.calls)
        self.feed(p, make_hand(), 30, t)
        self.assertEqual(len(be.calls), n1)                             # frozen: tidak ada output

    def test_latency_stats_collected(self):
        p = Pipeline(Config(preview=False), DryRunBackend())
        self.feed(p, make_hand(), 100, 0.0)                             # memicu report() sekali, tanpa error


if __name__ == "__main__":
    unittest.main()
