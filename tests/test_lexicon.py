"""Tests for lexicon loading, cache handling, and normalization."""

from __future__ import annotations

import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch

from pali_translator.lexicon import Lexicon, _fetch_json, _normalize

from tests.support import SAMPLE_RECORDS


class TestNormalize(unittest.TestCase):
    def test_ascii_term(self):
        self.assertEqual(_normalize("dukkha"), "dukkha")

    def test_diacritics_stripped(self):
        self.assertEqual(_normalize("nibbāna"), "nibbana")

    def test_case_insensitive(self):
        self.assertEqual(_normalize("Dukkha"), "dukkha")

    def test_spaces_converted(self):
        self.assertEqual(_normalize("noble truth"), "noble_truth")

    def test_hyphens_converted(self):
        self.assertEqual(_normalize("non-ill-will"), "non_ill_will")


class TestLexiconCache(unittest.TestCase):
    def test_loads_from_cache_when_available(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_path = Path(tmp_dir) / "lexicon.json"
            cache_path.write_text(json.dumps(SAMPLE_RECORDS), encoding="utf-8")

            lexicon = Lexicon(cache_path=cache_path)

            self.assertTrue(lexicon.loaded_from_cache)
            self.assertEqual(len(lexicon), len(SAMPLE_RECORDS))
            self.assertEqual(lexicon.lookup("dukkha")["preferred_translation"], "dissatisfaction")
            self.assertEqual(lexicon.info()["cache_path"], str(cache_path))

    @patch("pali_translator.lexicon._fetch_lexicon_from_github")
    def test_refresh_ignores_existing_cache(self, mock_fetch):
        mock_fetch.return_value = SAMPLE_RECORDS

        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_path = Path(tmp_dir) / "lexicon.json"
            cache_path.write_text("{}", encoding="utf-8")

            lexicon = Lexicon(cache_path=cache_path, refresh=True)

            self.assertFalse(lexicon.loaded_from_cache)
            self.assertEqual(len(lexicon), len(SAMPLE_RECORDS))
            mock_fetch.assert_called_once()

    def test_corrupt_cache_raises_runtime_error(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_path = Path(tmp_dir) / "lexicon.json"
            cache_path.write_text("not-json", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "Failed to read lexicon cache"):
                Lexicon(cache_path=cache_path)

    def test_empty_cache_raises_runtime_error(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_path = Path(tmp_dir) / "lexicon.json"
            cache_path.write_text("{}", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "empty or invalid"):
                Lexicon(cache_path=cache_path)

    @patch("pali_translator.lexicon._fetch_lexicon_from_github")
    def test_empty_fetch_raises_runtime_error(self, mock_fetch):
        mock_fetch.return_value = {}

        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_path = Path(tmp_dir) / "lexicon.json"

            with self.assertRaisesRegex(RuntimeError, "no term records were loaded"):
                Lexicon(cache_path=cache_path, refresh=True)

    @patch("pali_translator.lexicon.json.dump", side_effect=OSError("disk full"))
    @patch("pali_translator.lexicon._fetch_lexicon_from_github")
    def test_cache_write_failure_sets_warning(self, mock_fetch, _mock_dump):
        mock_fetch.return_value = SAMPLE_RECORDS

        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_path = Path(tmp_dir) / "lexicon.json"

            lexicon = Lexicon(cache_path=cache_path, refresh=True)

            self.assertIsNotNone(lexicon.cache_warning)
            self.assertIn("cache could not be written", lexicon.cache_warning)


class TestFetchJson(unittest.TestCase):
    @patch("pali_translator.lexicon.urllib.request.urlopen")
    def test_fetch_json_wraps_http_403(self, mock_urlopen):
        request = Mock()
        request.full_url = "https://example.invalid"
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url=request.full_url,
            code=403,
            msg="forbidden",
            hdrs=None,
            fp=None,
        )

        with self.assertRaisesRegex(RuntimeError, "GitHub API returned 403"):
            _fetch_json(request.full_url)

    @patch("pali_translator.lexicon.urllib.request.urlopen")
    def test_fetch_json_wraps_network_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("offline")

        with self.assertRaisesRegex(RuntimeError, "Failed to fetch"):
            _fetch_json("https://example.invalid")