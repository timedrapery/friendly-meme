"""CLI smoke tests for pali_translator."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

from pali_translator import cli
from pali_translator.translator import TermMatch, TranslationResult


def _fake_lexicon() -> MagicMock:
    lexicon = MagicMock()
    lexicon.loaded_from_cache = True
    lexicon.cache_warning = None
    lexicon.cache_path = Path("cache.json")
    lexicon.__len__.return_value = 4
    lexicon.info.return_value = {
        "entries": 4,
        "cache_path": "cache.json",
        "loaded_from_cache": True,
        "cache_exists": True,
    }
    return lexicon


class TestCli(unittest.TestCase):
    def _run(self, argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = cli.main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_no_input_prints_help(self):
        code, stdout, stderr = self._run([])
        self.assertEqual(code, 0)
        self.assertIn("Examples:", stdout)
        self.assertIn("pali-translator dukkha", stdout)
        self.assertEqual(stderr, "")

    @patch("pali_translator.cli.lookup_term")
    @patch("pali_translator.cli.Lexicon")
    def test_lookup_not_found_exits_with_one(self, mock_lexicon_cls, mock_lookup_term):
        mock_lexicon_cls.return_value = _fake_lexicon()
        mock_lookup_term.return_value = None

        code, stdout, stderr = self._run(["missing"])

        self.assertEqual(code, 1)
        self.assertIn("not found", stdout)
        self.assertIn("Loaded lexicon", stderr)

    @patch("pali_translator.cli.lookup_term")
    @patch("pali_translator.cli.Lexicon")
    def test_lookup_json_output(self, mock_lexicon_cls, mock_lookup_term):
        mock_lexicon_cls.return_value = _fake_lexicon()
        mock_lookup_term.return_value = TermMatch(
            token="dukkha",
            preferred_translation="dissatisfaction",
            alternative_translations=["stress"],
            definition="A test definition.",
            entry_type="major",
        )

        code, stdout, _stderr = self._run(["--json", "dukkha"])

        self.assertEqual(code, 0)
        self.assertIn('"mode": "lookup"', stdout)
        self.assertIn('"found": true', stdout)
        self.assertIn('"preferred_translation": "dissatisfaction"', stdout)

    @patch("pali_translator.cli.translate_text")
    @patch("pali_translator.cli.Lexicon")
    def test_translate_json_output(self, mock_lexicon_cls, mock_translate_text):
        mock_lexicon_cls.return_value = _fake_lexicon()
        mock_translate_text.return_value = TranslationResult(
            original="dukkha nibbana",
            translated="dissatisfaction unbinding",
            matches=[
                TermMatch(token="dukkha", preferred_translation="dissatisfaction"),
                TermMatch(token="nibbana", preferred_translation="unbinding"),
            ],
            unknown_tokens=[],
        )

        code, stdout, _stderr = self._run(["--json", "--translate", "dukkha nibbana"])

        self.assertEqual(code, 0)
        self.assertIn('"mode": "translate"', stdout)
        self.assertIn('"translated": "dissatisfaction unbinding"', stdout)

    @patch("pali_translator.cli.lookup_term")
    @patch("pali_translator.cli.Lexicon")
    def test_cache_path_is_forwarded(self, mock_lexicon_cls, mock_lookup_term):
        lexicon = _fake_lexicon()
        mock_lexicon_cls.return_value = lexicon
        mock_lookup_term.return_value = None

        code, _stdout, _stderr = self._run(["--cache-path", "tmp/lexicon.json", "dukkha"])

        self.assertEqual(code, 1)
        kwargs = mock_lexicon_cls.call_args.kwargs
        self.assertEqual(kwargs["cache_path"], Path("tmp/lexicon.json"))
        self.assertFalse(kwargs["refresh"])

    @patch("pali_translator.cli.Lexicon")
    def test_load_error_exits_with_two(self, mock_lexicon_cls):
        mock_lexicon_cls.side_effect = RuntimeError("cache is broken")

        code, stdout, stderr = self._run(["dukkha"])

        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("Error: cache is broken", stderr)

    @patch("pali_translator.cli.Lexicon")
    def test_info_mode_without_input(self, mock_lexicon_cls):
        mock_lexicon_cls.return_value = _fake_lexicon()

        code, stdout, stderr = self._run(["--info"])

        self.assertEqual(code, 0)
        self.assertIn("Lexicon status:", stdout)
        self.assertIn("entries", stdout)
        self.assertIn("Loaded lexicon", stderr)

    @patch("pali_translator.cli.Lexicon")
    def test_info_mode_json(self, mock_lexicon_cls):
        mock_lexicon_cls.return_value = _fake_lexicon()

        code, stdout, _stderr = self._run(["--info", "--json"])

        self.assertEqual(code, 0)
        self.assertIn('"mode": "info"', stdout)
        self.assertIn('"entries": 4', stdout)