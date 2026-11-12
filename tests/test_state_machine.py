import unittest

from gesture_core.config import Config
from gesture_core.cursor_mapper import CursorMapper
from gesture_core.state_machine import GestureStateMachine, State
from gesture_core.types import FIST, NONE, OPEN_PALM, PINCH, SHAKA, TWO_FINGER
from tests.synth import ev

FPS = 30


class Driver:
    """Menyuapi state machine pada 30 fps dan mengumpulkan perintah."""
    def __init__(self, cfg=None):
        self.sm = GestureStateMachine(cfg or Config())
        self.i = 0
        self.cmds = []

    def feed(self, label, n=1, **kw):
        out = []
        for _ in range(n):
            t = self.i / FPS
            e = None if label is None else ev(label, t=t, **kw)
            out += self.sm.update(e, t)
            self.i += 1
        self.cmds += out
        return out

    def count(self, action, cmds=None):
        return sum(1 for c in (self.cmds if cmds is None else cmds) if c.action == action)


class StateMachineTests(unittest.TestCase):
    def test_open_palm_enters_cursor_and_emits_targets(self):
        d = Driver()
        d.feed(OPEN_PALM, 10)
        self.assertEqual(d.sm.state, State.CURSOR_ACTIVE)
        self.assertGreater(d.count("cursor_target"), 5)
        self.assertEqual(d.count("reset_smoothing"), 1)

    def test_single_click_while_pinch_held(self):
        d = Driver()
        d.feed(OPEN_PALM, 10)
        d.feed(PINCH, 40)                       # tahan > 1 detik
        self.assertEqual(d.count("click"), 1)   # FR-03: tidak ada klik berulang
        self.assertEqual(d.sm.state, State.CLICK_PENDING)

    def test_cursor_frozen_while_pinching(self):
        d = Driver()
        d.feed(OPEN_PALM, 10)
        n = d.count("cursor_target")
        d.feed(PINCH, 10, palm=(0.9, 0.9))
        self.assertEqual(d.count("cursor_target"), n)

    def test_second_pinch_after_release_clicks_again(self):
        d = Driver()
        d.feed(OPEN_PALM, 10)
        d.feed(PINCH, 6)
        d.feed(OPEN_PALM, 6)
        d.feed(PINCH, 6)
        self.assertEqual(d.count("click"), 2)    # basis double-click (OS menggabungkan)

    def test_double_pinch_interval_within_400ms(self):
        d = Driver()
        d.feed(OPEN_PALM, 10)
        first = d.feed(PINCH, 3)
        d.feed(OPEN_PALM, 3)
        second = d.feed(PINCH, 3)
        t1 = [c.timestamp_ms for c in first if c.action == "click"][0]
        t2 = [c.timestamp_ms for c in second if c.action == "click"][0]
        self.assertLessEqual(t2 - t1, 400)

    def test_pinch_ignored_from_idle(self):
        d = Driver()
        d.feed(PINCH, 20)
        self.assertEqual(d.count("click"), 0)

    def test_post_click_cursor_lock(self):
        d = Driver()
        d.feed(OPEN_PALM, 10)
        d.feed(PINCH, 3)
        out = d.feed(OPEN_PALM, 6)               # 0.2 s setelah klik < 0.4 s lock
        self.assertEqual(d.count("cursor_target", out), 0)
        out = d.feed(OPEN_PALM, 15)
        self.assertGreater(d.count("cursor_target", out), 0)

    def test_transient_label_flicker_is_ignored(self):
        d = Driver()
        d.feed(OPEN_PALM, 10)
        d.feed(FIST, 1)                          # < confirm_frames
        d.feed(OPEN_PALM, 3)
        self.assertEqual(d.sm.state, State.CURSOR_ACTIVE)

    def test_hand_lost_returns_to_idle_after_grace(self):
        d = Driver()
        d.feed(OPEN_PALM, 10)
        d.feed(None, 3)                          # 0.1 s < grace
        self.assertEqual(d.sm.state, State.CURSOR_ACTIVE)
        d.feed(None, 10)
        self.assertEqual(d.sm.state, State.IDLE)

    def test_scroll_rate_control(self):
        d = Driver()
        d.feed(TWO_FINGER, 6, scroll_y=0.50)     # anchor
        self.assertEqual(d.sm.state, State.SCROLL_ACTIVE)
        out = d.feed(TWO_FINGER, 10, scroll_y=0.49)    # di dalam deadzone
        self.assertEqual(d.count("scroll", out), 0)
        out = d.feed(TWO_FINGER, 10, scroll_y=0.40)    # naik 0.10 -> scroll naik
        notches = [c.params["notches"] for c in out if c.action == "scroll"]
        self.assertTrue(notches and all(n > 0 for n in notches))
        out = d.feed(TWO_FINGER, 10, scroll_y=0.60)    # turun -> negatif
        notches = [c.params["notches"] for c in out if c.action == "scroll"]
        self.assertTrue(notches and all(n < 0 for n in notches))

    def test_scroll_and_cursor_mutually_exclusive(self):
        d = Driver()
        d.feed(OPEN_PALM, 6)
        out = d.feed(TWO_FINGER, 10, scroll_y=0.3)
        self.assertEqual(d.count("cursor_target", out[2:]), 0)
        self.assertEqual(d.sm.state, State.SCROLL_ACTIVE)

    def test_scroll_max_rate_capped(self):
        cfg = Config()
        d = Driver(cfg)
        d.feed(TWO_FINGER, 6, scroll_y=0.9)
        out = d.feed(TWO_FINGER, 10, scroll_y=0.0)
        per_frame = max(c.params["notches"] for c in out if c.action == "scroll")
        self.assertLessEqual(per_frame, cfg.scroll_max_rate / FPS + 1e-6)

    def test_freeze_by_shaka_hold_and_unfreeze(self):
        d = Driver()
        d.feed(OPEN_PALM, 10)
        d.feed(SHAKA, int(1.5 * FPS))
        self.assertNotEqual(d.sm.state, State.FROZEN)      # belum 2 detik
        d.feed(SHAKA, int(0.8 * FPS))
        self.assertEqual(d.sm.state, State.FROZEN)
        out = d.feed(OPEN_PALM, 30)                        # frozen: semua input dibuang
        self.assertEqual(len(out), 0)
        d.feed(SHAKA, int(2.3 * FPS))
        self.assertEqual(d.sm.state, State.IDLE)

    def test_freeze_toggles_once_per_hold(self):
        d = Driver()
        d.feed(SHAKA, int(5 * FPS))
        self.assertEqual(d.count("freeze"), 1)

    def test_freeze_hotkey_toggle(self):
        d = Driver()
        d.feed(OPEN_PALM, 6)
        d.sm.request_freeze_toggle()
        d.feed(OPEN_PALM, 1)
        self.assertEqual(d.sm.state, State.FROZEN)
        d.sm.request_freeze_toggle()
        d.feed(OPEN_PALM, 1)
        self.assertEqual(d.count("freeze"), 2)
        self.assertEqual(d.sm.state, State.CURSOR_ACTIVE)   # telapak masih terbuka -> lanjut

    def test_fist_is_inert_in_phase0(self):
        d = Driver()
        d.feed(OPEN_PALM, 6)
        d.feed(FIST, 15)
        self.assertEqual(d.count("click"), 0)
        self.assertEqual(d.sm.state, State.IDLE)


class CursorMapperTests(unittest.TestCase):
    def test_region_corners_map_to_screen_corners(self):
        cfg = Config()
        m = CursorMapper(cfg, 1920, 1080)
        x0, y0, x1, y1 = cfg.active_region
        self.assertEqual(m.map(x0, y0, 0.0), (0, 0))
        m.reset()
        self.assertEqual(m.map(x1, y1, 0.0), (1919, 1079))
        m.reset()
        self.assertEqual(m.map(-1, 2, 0.0), (0, 1079))   # clamp di luar region

    def test_gap_resets_filter(self):
        m = CursorMapper(Config(), 1000, 1000)
        m.map(0.5, 0.45, 0.0)
        x, _ = m.map(0.8, 0.45, 5.0)                      # jeda panjang: tanpa smoothing
        self.assertEqual(x, 999)


if __name__ == "__main__":
    unittest.main()
