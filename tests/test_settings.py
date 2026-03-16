"""Tests for pali_translator.gui.settings — AppSettings load/save/defaults."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from pali_translator.gui.settings import AppSettings, DEFAULT_SETTINGS_PATH


class TestAppSettingsDefaults(unittest.TestCase):
    """Instantiating AppSettings without arguments returns sane defaults."""

    def test_default_font_size(self):
        s = AppSettings()
        self.assertEqual(s.font_size, 12)

    def test_default_history_size(self):
        s = AppSettings()
        self.assertEqual(s.history_size, 25)

    def test_default_last_export_dir(self):
        s = AppSettings()
        self.assertEqual(s.last_export_dir, "")

    def test_default_concordance_sort(self):
        s = AppSettings()
        self.assertEqual(s.concordance_sort, "frequency")

    def test_default_auto_copy(self):
        s = AppSettings()
        self.assertFalse(s.auto_copy)


class TestAppSettingsLoad(unittest.TestCase):
    """AppSettings.load() correctly reads values from a JSON file."""

    def setUp(self) -> None:
        import tempfile
        self._tmp = tempfile.mkdtemp()
        self._path = Path(self._tmp) / "settings.json"

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _write(self, data: dict) -> None:
        self._path.write_text(json.dumps(data), encoding="utf-8")

    def test_loads_font_size(self):
        self._write({"font_size": 16})
        s = AppSettings.load(self._path)
        self.assertEqual(s.font_size, 16)

    def test_loads_history_size(self):
        self._write({"history_size": 10})
        s = AppSettings.load(self._path)
        self.assertEqual(s.history_size, 10)

    def test_loads_concordance_sort(self):
        self._write({"concordance_sort": "alpha"})
        s = AppSettings.load(self._path)
        self.assertEqual(s.concordance_sort, "alpha")

    def test_loads_auto_copy(self):
        self._write({"auto_copy": True})
        s = AppSettings.load(self._path)
        self.assertTrue(s.auto_copy)

    def test_loads_last_export_dir(self):
        self._write({"last_export_dir": "/tmp/exports"})
        s = AppSettings.load(self._path)
        self.assertEqual(s.last_export_dir, "/tmp/exports")

    def test_clamps_font_size_min(self):
        self._write({"font_size": 2})
        s = AppSettings.load(self._path)
        self.assertEqual(s.font_size, 8)

    def test_clamps_font_size_max(self):
        self._write({"font_size": 100})
        s = AppSettings.load(self._path)
        self.assertEqual(s.font_size, 24)

    def test_clamps_history_size_min(self):
        self._write({"history_size": 0})
        s = AppSettings.load(self._path)
        self.assertEqual(s.history_size, 1)

    def test_clamps_history_size_max(self):
        self._write({"history_size": 9999})
        s = AppSettings.load(self._path)
        self.assertEqual(s.history_size, 100)

    def test_ignores_invalid_concordance_sort(self):
        self._write({"concordance_sort": "nonsense"})
        s = AppSettings.load(self._path)
        self.assertEqual(s.concordance_sort, "frequency")  # default

    def test_ignores_unknown_key(self):
        self._write({"unknown_future_key": "lalala"})
        s = AppSettings.load(self._path)
        self.assertEqual(s.font_size, 12)  # defaults intact

    def test_missing_file_returns_defaults(self):
        s = AppSettings.load(self._path)  # file doesn't exist yet
        self.assertEqual(s.font_size, 12)

    def test_corrupt_json_returns_defaults(self):
        self._path.write_text("{not valid json", encoding="utf-8")
        s = AppSettings.load(self._path)
        self.assertEqual(s.font_size, 12)


class TestAppSettingsSave(unittest.TestCase):
    """AppSettings.save() correctly persists values."""

    def setUp(self) -> None:
        import tempfile
        self._tmp = tempfile.mkdtemp()
        self._path = Path(self._tmp) / "settings.json"

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_round_trip(self):
        s = AppSettings(font_size=14, history_size=10, concordance_sort="alpha", auto_copy=True)
        s.save(self._path)
        s2 = AppSettings.load(self._path)
        self.assertEqual(s2.font_size, 14)
        self.assertEqual(s2.history_size, 10)
        self.assertEqual(s2.concordance_sort, "alpha")
        self.assertTrue(s2.auto_copy)

    def test_creates_parent_dir(self):
        deep_path = Path(self._tmp) / "nested" / "deep" / "settings.json"
        s = AppSettings()
        s.save(deep_path)
        self.assertTrue(deep_path.exists())


if __name__ == "__main__":
    unittest.main()
