import unittest

from gesture_core.classifier import HeuristicClassifier
from gesture_core.config import Config
from gesture_core.types import FIST, OPEN_PALM, PINCH, SHAKA, TWO_FINGER
from tests.synth import make_hand


class ClassifierTests(unittest.TestCase):
    def setUp(self):
        self.c = HeuristicClassifier(Config())

    def lab(self, hand):
        return self.c.classify(hand, 0).label

    def test_open_palm(self):
        self.assertEqual(self.lab(make_hand()), OPEN_PALM)

    def test_open_palm_ignores_thumb(self):
        self.assertEqual(self.lab(make_hand(thumb=False)), OPEN_PALM)

    def test_pinch(self):
        self.assertEqual(self.lab(make_hand(pinch=True)), PINCH)

    def test_fist_is_not_pinch(self):
        self.assertEqual(self.lab(make_hand(False, False, False, False, thumb=False)), FIST)

    def test_two_finger(self):
        self.assertEqual(self.lab(make_hand(True, True, False, False, thumb=False)), TWO_FINGER)

    def test_shaka(self):
        self.assertEqual(self.lab(make_hand(False, False, False, True, thumb=True)), SHAKA)

    def test_shaka_distinct_from_fist_and_palm(self):
        self.assertNotEqual(self.lab(make_hand(False, False, False, True, thumb=True)), FIST)

    def test_pinch_hysteresis(self):
        h = make_hand(pinch=True)
        self.assertEqual(self.lab(h), PINCH)
        # rasio ~0.37: di antara pinch_on (0.28) dan pinch_off (0.42) -> tetap pinch
        h.points[4, 0] -= 0.035
        self.assertEqual(self.lab(h), PINCH)
        h.points[4, 0] -= 0.20                      # jauh: lepas
        self.assertNotEqual(self.lab(h), PINCH)

    def test_rotation_invariance(self):
        import numpy as np
        h = make_hand()
        ang = np.deg2rad(60)
        rot = np.array([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]])
        c = h.points[0, :2].copy()
        # rotasi di ruang piksel-benar (koreksi aspek) agar bentuk tangan tidak terdistorsi
        a = self.c.cfg.aspect
        xy = (h.points[:, :2] - c) * np.array([a, 1.0])
        xy = xy @ rot.T / np.array([a, 1.0]) + c
        h.points[:, :2] = xy
        self.assertEqual(self.lab(h), OPEN_PALM)

    def test_palm_center_metadata(self):
        ev = self.c.classify(make_hand(dx=0.1, dy=-0.1), 0)
        self.assertAlmostEqual(ev.metadata["palm_x"], 0.5 + 0.1 + (0.44 + 0.50 + 0.56 + 0.61 - 4 * 0.50) / 5 + 0.0, delta=0.05)


if __name__ == "__main__":
    unittest.main()
