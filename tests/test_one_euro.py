import random
import statistics
import unittest

from gesture_core.one_euro import OneEuroFilter


class OneEuroTests(unittest.TestCase):
    def test_constant_signal_passthrough(self):
        f = OneEuroFilter()
        for i in range(50):
            self.assertAlmostEqual(f(100.0, i / 30), 100.0, places=6)

    def test_attenuates_jitter_when_still(self):
        rnd = random.Random(1)
        f = OneEuroFilter(min_cutoff=1.0, beta=0.02)
        raw = [500 + rnd.uniform(-5, 5) for _ in range(300)]
        out = [f(x, i / 30) for i, x in enumerate(raw)]
        sd = lambda v: statistics.pstdev(v[60:])
        self.assertLess(sd(out), sd(raw) * 0.5)

    def test_tracks_fast_motion_with_low_lag(self):
        f = OneEuroFilter(min_cutoff=1.0, beta=0.02)
        out = [f(i * 40.0, i / 30) for i in range(60)]      # 1200 px/s
        self.assertLess(abs(out[-1] - 59 * 40.0), 120)       # lag < 3 frame-ish saat cepat

    def test_reset(self):
        f = OneEuroFilter()
        f(10, 0.0); f(20, 0.03)
        f.reset()
        self.assertEqual(f(999, 1.0), 999)


if __name__ == "__main__":
    unittest.main()
