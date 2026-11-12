import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from gesture_core import config
from gesture_core.config import Config


class ConfigTests(unittest.TestCase):
    def test_default_model_path_in_models_dir(self):
        self.assertTrue(Config().model_path.endswith("hand_landmarker.task"))

    def test_resource_root_when_frozen(self):
        with mock.patch.object(sys, "frozen", True, create=True), \
             mock.patch.object(sys, "_MEIPASS", "/tmp/_internal", create=True):
            self.assertEqual(config._resource_root(), Path("/tmp/_internal"))

    def test_resource_root_in_dev(self):
        self.assertTrue((config._resource_root() / "gesture_core").is_dir())

    def test_from_json_rejects_unknown_keys(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write('{"tidak_ada": 1}')
        with self.assertRaises(ValueError):
            Config.from_json(f.name)

    def test_from_json_override(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write('{"pinch_on": 0.2, "active_region": [0.1, 0.1, 0.9, 0.9]}')
        c = Config.from_json(f.name)
        self.assertEqual(c.pinch_on, 0.2)
        self.assertEqual(c.active_region, (0.1, 0.1, 0.9, 0.9))


if __name__ == "__main__":
    unittest.main()
