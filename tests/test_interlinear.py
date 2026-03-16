"""Tests for pali_translator.gui.interlinear — InterlinearUnit + build_interlinear."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from pali_translator.gui.controller import TokenRow
from pali_translator.gui.interlinear import InterlinearUnit, build_interlinear
from pali_translator.phrases import PhraseMatch


def _row(token: str, matched: bool = True, preferred: str = "p",
         untranslated: bool = False) -> TokenRow:
    return TokenRow(
        token=token,
        normalized=token.lower(),
        matched=matched,
        preferred_translation=preferred,
        entry_type="major" if matched else "",
        untranslated_preferred=untranslated,
        definition="",
        alternatives=[],
    )


def _phrase(span: tuple, start: int, end: int, rendering: str = "the phrase") -> PhraseMatch:
    return PhraseMatch(
        span=span,
        normalized_span=tuple(t.lower() for t in span),
        start_pos=start,
        end_pos=end,
        preferred_rendering=rendering,
        entry_type="major",
        untranslated_preferred=False,
        source_key="_".join(t.lower() for t in span),
    )


class TestBuildInterlinearEmpty(unittest.TestCase):
    def test_empty_rows_empty_result(self):
        self.assertEqual(build_interlinear([], []), [])

    def test_no_phrases_simple_units(self):
        rows = [_row("dukkha"), _row("nibbana")]
        units = build_interlinear(rows, [])
        self.assertEqual(len(units), 2)
        self.assertFalse(units[0].is_phrase_start)
        self.assertFalse(units[0].is_phrase_end)


class TestBuildInterlinearGlosses(unittest.TestCase):
    def test_matched_token_gloss_is_preferred(self):
        rows = [_row("dukkha", matched=True, preferred="dissatisfaction")]
        units = build_interlinear(rows, [])
        self.assertEqual(units[0].gloss, "dissatisfaction")

    def test_unknown_token_gloss_is_question_marks(self):
        rows = [_row("xyz", matched=False, preferred="")]
        units = build_interlinear(rows, [])
        self.assertEqual(units[0].gloss, "???")

    def test_policy_token_gloss_is_pali(self):
        rows = [_row("dhamma", matched=True, preferred="dhamma", untranslated=True)]
        units = build_interlinear(rows, [])
        self.assertEqual(units[0].gloss, "dhamma")


class TestBuildInterlinearPhrases(unittest.TestCase):
    def test_phrase_start_flagged(self):
        rows = [_row("bodhi"), _row("citta"), _row("is")]
        phrases = [_phrase(("bodhi", "citta"), 0, 2, "mind of awakening")]
        units = build_interlinear(rows, phrases)
        self.assertTrue(units[0].is_phrase_start)
        self.assertFalse(units[2].is_phrase_start)

    def test_phrase_end_flagged(self):
        rows = [_row("bodhi"), _row("citta"), _row("is")]
        phrases = [_phrase(("bodhi", "citta"), 0, 2, "mind of awakening")]
        units = build_interlinear(rows, phrases)
        self.assertFalse(units[0].is_phrase_end)
        self.assertTrue(units[1].is_phrase_end)

    def test_phrase_rendering_on_start_cell(self):
        rows = [_row("bodhi"), _row("citta")]
        phrases = [_phrase(("bodhi", "citta"), 0, 2, "mind of awakening")]
        units = build_interlinear(rows, phrases)
        self.assertEqual(units[0].phrase_rendering, "mind of awakening")
        self.assertIsNone(units[1].phrase_rendering)

    def test_phrase_span_on_start_cell(self):
        rows = [_row("bodhi"), _row("citta")]
        phrases = [_phrase(("bodhi", "citta"), 0, 2)]
        units = build_interlinear(rows, phrases)
        self.assertEqual(units[0].phrase_span, ("bodhi", "citta"))

    def test_non_phrase_token_no_rendering(self):
        rows = [_row("bodhi"), _row("citta"), _row("dukkha")]
        phrases = [_phrase(("bodhi", "citta"), 0, 2)]
        units = build_interlinear(rows, phrases)
        self.assertIsNone(units[2].phrase_rendering)
        self.assertFalse(units[2].is_phrase_start)

    def test_multiple_phrases_both_flagged(self):
        rows = [_row("bodhi"), _row("citta"), _row("samma"), _row("sankappa")]
        phrases = [
            _phrase(("bodhi", "citta"), 0, 2),
            _phrase(("samma", "sankappa"), 2, 4),
        ]
        units = build_interlinear(rows, phrases)
        self.assertTrue(units[0].is_phrase_start)
        self.assertTrue(units[2].is_phrase_start)

    def test_unit_count_equals_row_count(self):
        rows = [_row(t) for t in ["a", "b", "c", "d", "e"]]
        phrases = [_phrase(("a", "b"), 0, 2)]
        units = build_interlinear(rows, phrases)
        self.assertEqual(len(units), 5)

    def test_token_and_normalized_preserved(self):
        rows = [_row("Dukkha")]
        units = build_interlinear(rows, [])
        self.assertEqual(units[0].token, "Dukkha")
        self.assertEqual(units[0].normalized, "dukkha")


if __name__ == "__main__":
    unittest.main()
