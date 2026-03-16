"""Tests for the GUI controller layer.

These tests cover all business-logic paths in
:mod:`pali_translator.gui.controller` without importing tkinter, so they run
correctly in headless / CI environments.

The test lexicon is intentionally injected via the internal ``_lexicon``
attribute (the same pattern used by the existing test suite) to avoid any
network access.
"""

from __future__ import annotations

import unittest

from pali_translator.gui.controller import (
    Controller,
    LexiconStatus,
    TokenRow,
    TranslationSession,
)
from pali_translator.lexicon import Lexicon
from tests.support import SAMPLE_RECORDS


def _make_ctrl() -> Controller:
    """Return a Controller pre-loaded with the offline sample lexicon."""
    ctrl = Controller()
    lexicon = Lexicon.from_dict(SAMPLE_RECORDS)
    ctrl._lexicon = lexicon
    ctrl._status = LexiconStatus(
        loaded=True,
        from_cache=True,
        cache_path="/tmp/test_lexicon.json",
        entry_count=len(lexicon),
    )
    return ctrl


class TestControllerInit(unittest.TestCase):
    def test_lexicon_not_ready_initially(self) -> None:
        ctrl = Controller()
        self.assertFalse(ctrl.lexicon_ready)

    def test_status_not_loaded_initially(self) -> None:
        ctrl = Controller()
        self.assertFalse(ctrl.status.loaded)

    def test_session_none_initially(self) -> None:
        ctrl = Controller()
        self.assertIsNone(ctrl.current_session)

    def test_translate_raises_when_no_lexicon(self) -> None:
        ctrl = Controller()
        with self.assertRaises(RuntimeError):
            ctrl.translate("dukkha")

    def test_lookup_raises_when_no_lexicon(self) -> None:
        ctrl = Controller()
        with self.assertRaises(RuntimeError):
            ctrl.lookup("dukkha")


class TestControllerTranslate(unittest.TestCase):
    def setUp(self) -> None:
        self.ctrl = _make_ctrl()

    def test_lexicon_ready_after_injection(self) -> None:
        self.assertTrue(self.ctrl.lexicon_ready)

    def test_translate_returns_correct_translation(self) -> None:
        result = self.ctrl.translate("dukkha nibbana")
        self.assertEqual(result.translated, "dissatisfaction unbinding")

    def test_translate_records_session(self) -> None:
        self.ctrl.translate("dukkha")
        self.assertIsNotNone(self.ctrl.current_session)

    def test_session_source_text_preserved(self) -> None:
        self.ctrl.translate("dukkha nibbana")
        self.assertEqual(self.ctrl.current_session.source_text, "dukkha nibbana")

    def test_session_is_replaced_on_second_translate(self) -> None:
        self.ctrl.translate("dukkha")
        self.ctrl.translate("nibbana")
        self.assertEqual(self.ctrl.current_session.source_text, "nibbana")

    def test_session_carries_lexicon_status(self) -> None:
        self.ctrl.translate("dukkha")
        session = self.ctrl.current_session
        self.assertTrue(session.lexicon_status.loaded)
        self.assertTrue(session.lexicon_status.from_cache)

    def test_session_timestamp_is_set(self) -> None:
        self.ctrl.translate("dukkha")
        ts = self.ctrl.current_session.timestamp
        self.assertIsInstance(ts, str)
        self.assertGreater(len(ts), 0)


class TestControllerTokenRows(unittest.TestCase):
    def setUp(self) -> None:
        self.ctrl = _make_ctrl()

    def test_token_rows_count_matches_tokens(self) -> None:
        self.ctrl.translate("dukkha nibbana dhamma")
        rows = self.ctrl.current_session.token_rows
        self.assertEqual(len(rows), 3)

    def test_matched_row_fields(self) -> None:
        self.ctrl.translate("dukkha")
        row = self.ctrl.current_session.token_rows[0]
        self.assertIsInstance(row, TokenRow)
        self.assertTrue(row.matched)
        self.assertEqual(row.token, "dukkha")
        self.assertEqual(row.normalized, "dukkha")
        self.assertEqual(row.preferred_translation, "dissatisfaction")
        self.assertEqual(row.entry_type, "major")
        self.assertFalse(row.untranslated_preferred)

    def test_untranslated_preferred_row(self) -> None:
        self.ctrl.translate("dhamma")
        row = self.ctrl.current_session.token_rows[0]
        self.assertTrue(row.matched)
        self.assertTrue(row.untranslated_preferred)
        self.assertEqual(row.preferred_translation, "dhamma")

    def test_unknown_token_row(self) -> None:
        self.ctrl.translate("zznotaword")
        row = self.ctrl.current_session.token_rows[0]
        self.assertFalse(row.matched)
        self.assertEqual(row.preferred_translation, "")
        self.assertEqual(row.entry_type, "")
        self.assertFalse(row.untranslated_preferred)

    def test_mixed_known_and_unknown_rows(self) -> None:
        self.ctrl.translate("dukkha zzunknown nibbana")
        rows = self.ctrl.current_session.token_rows
        self.assertEqual(len(rows), 3)
        self.assertTrue(rows[0].matched)
        self.assertFalse(rows[1].matched)
        self.assertTrue(rows[2].matched)

    def test_alternatives_in_row(self) -> None:
        self.ctrl.translate("dukkha")
        row = self.ctrl.current_session.token_rows[0]
        self.assertIn("unsatisfactoriness", row.alternatives)

    def test_punctuation_stripped_for_row(self) -> None:
        self.ctrl.translate("dukkha,")
        row = self.ctrl.current_session.token_rows[0]
        self.assertTrue(row.matched)
        self.assertEqual(row.normalized, "dukkha")

    def test_empty_text_gives_no_rows(self) -> None:
        self.ctrl.translate("")
        rows = self.ctrl.current_session.token_rows
        self.assertEqual(rows, [])


class TestControllerLookup(unittest.TestCase):
    def setUp(self) -> None:
        self.ctrl = _make_ctrl()

    def test_lookup_known_term(self) -> None:
        match = self.ctrl.lookup("dukkha")
        self.assertIsNotNone(match)
        self.assertEqual(match.preferred_translation, "dissatisfaction")

    def test_lookup_diacritic_variant(self) -> None:
        # nibbāna (with macron) should resolve via normalisation
        match = self.ctrl.lookup("nibbāna")
        self.assertIsNotNone(match)
        self.assertEqual(match.preferred_translation, "unbinding")

    def test_lookup_unknown_term_returns_none(self) -> None:
        result = self.ctrl.lookup("zznotaword")
        self.assertIsNone(result)

    def test_lookup_does_not_affect_session(self) -> None:
        self.ctrl.lookup("dukkha")
        self.assertIsNone(self.ctrl.current_session)
