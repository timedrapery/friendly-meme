"""Tests for pali_translator.phrases — multi-word phrase matching."""

from __future__ import annotations

import unittest

from pali_translator.lexicon import Lexicon
from pali_translator.phrases import PhraseMatch, match_phrases, _build_phrase_index


def _make_lexicon_with_phrases() -> Lexicon:
    """Return a Lexicon containing a few single-word and multi-word entries."""
    data = {
        "dukkha": {
            "term": "dukkha",
            "normalized_term": "dukkha",
            "entry_type": "major",
            "preferred_translation": "dissatisfaction",
            "untranslated_preferred": False,
        },
        "nibbana": {
            "term": "nibbāna",
            "normalized_term": "nibbana",
            "entry_type": "major",
            "preferred_translation": "unbinding",
            "untranslated_preferred": False,
        },
        "bodhi_citta": {
            "term": "bodhi citta",
            "normalized_term": "bodhi_citta",
            "entry_type": "major",
            "preferred_translation": "mind of awakening",
            "untranslated_preferred": False,
        },
        "samma_sankappa": {
            "term": "sammā saṅkappa",
            "normalized_term": "samma_sankappa",
            "entry_type": "major",
            "preferred_translation": "right intention",
            "untranslated_preferred": False,
        },
        "anicca_dukkha_anatta": {
            "term": "anicca dukkha anatta",
            "normalized_term": "anicca_dukkha_anatta",
            "entry_type": "major",
            "preferred_translation": "impermanence dissatisfaction non-self",
            "untranslated_preferred": True,
        },
    }
    return Lexicon.from_dict(data)


class TestBuildPhraseIndex(unittest.TestCase):
    def test_includes_multi_word_entries(self):
        lex = _make_lexicon_with_phrases()
        index = _build_phrase_index(lex)
        self.assertIn(("bodhi", "citta"), index)

    def test_excludes_single_word_entries(self):
        lex = _make_lexicon_with_phrases()
        index = _build_phrase_index(lex)
        # "dukkha" is single-word
        for key in index:
            self.assertGreater(len(key), 1)

    def test_three_word_entry_included(self):
        lex = _make_lexicon_with_phrases()
        index = _build_phrase_index(lex)
        self.assertIn(("anicca", "dukkha", "anatta"), index)


class TestMatchPhrases(unittest.TestCase):
    def setUp(self) -> None:
        self.lex = _make_lexicon_with_phrases()

    def test_empty_tokens_returns_empty(self):
        self.assertEqual(match_phrases([], self.lex), [])

    def test_no_phrase_tokens_returns_empty(self):
        tokens = ["dukkha", "is", "real"]
        result = match_phrases(tokens, self.lex)
        self.assertEqual(result, [])

    def test_simple_two_word_phrase(self):
        tokens = ["bodhi", "citta"]
        result = match_phrases(tokens, self.lex)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].span, ("bodhi", "citta"))
        self.assertEqual(result[0].start_pos, 0)
        self.assertEqual(result[0].end_pos, 2)

    def test_phrase_in_larger_context(self):
        tokens = ["the", "bodhi", "citta", "is", "important"]
        result = match_phrases(tokens, self.lex)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].start_pos, 1)
        self.assertEqual(result[0].end_pos, 3)

    def test_three_word_phrase_found(self):
        tokens = ["anicca", "dukkha", "anatta"]
        result = match_phrases(tokens, self.lex)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].span, ("anicca", "dukkha", "anatta"))

    def test_longest_match_wins(self):
        # "anicca dukkha anatta" should beat "bodhi citta" where spans overlap
        tokens = ["anicca", "dukkha", "anatta"]
        result = match_phrases(tokens, self.lex)
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0].span), 3)

    def test_non_overlapping(self):
        tokens = ["bodhi", "citta", "samma", "sankappa"]
        result = match_phrases(tokens, self.lex)
        self.assertEqual(len(result), 2)
        # Both phrases should be found, non-overlapping
        starts = [r.start_pos for r in result]
        self.assertNotIn(1, starts)  # no overlap
        self.assertIn(0, starts)
        self.assertIn(2, starts)

    def test_phrase_preferred_rendering(self):
        tokens = ["bodhi", "citta"]
        result = match_phrases(tokens, self.lex)
        self.assertEqual(result[0].preferred_rendering, "mind of awakening")

    def test_phrase_source_key(self):
        tokens = ["bodhi", "citta"]
        result = match_phrases(tokens, self.lex)
        self.assertEqual(result[0].source_key, "bodhi_citta")

    def test_phrase_normalized_span(self):
        tokens = ["bodhi", "citta"]
        result = match_phrases(tokens, self.lex)
        self.assertEqual(result[0].normalized_span, ("bodhi", "citta"))

    def test_results_ordered_by_start_pos(self):
        tokens = ["samma", "sankappa", "x", "bodhi", "citta"]
        result = match_phrases(tokens, self.lex)
        starts = [r.start_pos for r in result]
        self.assertEqual(starts, sorted(starts))

    def test_untranslated_preferred_flag(self):
        tokens = ["anicca", "dukkha", "anatta"]
        result = match_phrases(tokens, self.lex)
        self.assertTrue(result[0].untranslated_preferred)

    def test_empty_lexicon_returns_empty(self):
        empty_lex = Lexicon.from_dict({})
        result = match_phrases(["bodhi", "citta"], empty_lex)
        self.assertEqual(result, [])

    def test_punctuation_stripped_for_matching(self):
        tokens = ["bodhi,", "citta."]
        result = match_phrases(tokens, self.lex)
        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()
