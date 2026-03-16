"""Tests for translator-facing behavior and normalization consistency."""

from __future__ import annotations

import unittest

from pali_translator.lexicon import Lexicon, _normalize as lex_normalize
from pali_translator.translator import lookup_term, translate_text, _normalize as tr_normalize

from tests.support import SAMPLE_RECORDS

LEXICON = Lexicon.from_dict(SAMPLE_RECORDS)


class TestLookupTerm(unittest.TestCase):
    def test_known_term_returns_match(self):
        match = lookup_term("dukkha", LEXICON)
        self.assertIsNotNone(match)
        self.assertEqual(match.preferred_translation, "dissatisfaction")
        self.assertIn("unsatisfactoriness", match.alternative_translations)

    def test_untranslated_preferred_flag(self):
        match = lookup_term("dhamma", LEXICON)
        self.assertIsNotNone(match)
        self.assertTrue(match.untranslated_preferred)
        # When untranslated_preferred, preferred_translation holds the original term
        self.assertEqual(match.preferred_translation, "dhamma")

    def test_unknown_term_returns_none(self):
        self.assertIsNone(lookup_term("zzunknown", LEXICON))

    def test_minor_term(self):
        match = lookup_term("ajiva", LEXICON)
        self.assertIsNotNone(match)
        self.assertEqual(match.preferred_translation, "livelihood")
        self.assertEqual(match.entry_type, "minor")


class TestTranslateText(unittest.TestCase):
    def test_single_known_word(self):
        result = translate_text("dukkha", LEXICON)
        self.assertEqual(result.translated, "dissatisfaction")
        self.assertEqual(len(result.matches), 1)
        self.assertEqual(result.unknown_tokens, [])

    def test_multiple_known_words(self):
        result = translate_text("dukkha nibbana ajiva", LEXICON)
        self.assertIn("dissatisfaction", result.translated)
        self.assertIn("unbinding", result.translated)
        self.assertIn("livelihood", result.translated)
        self.assertEqual(len(result.matches), 3)

    def test_untranslated_preferred_kept_in_output(self):
        result = translate_text("dhamma", LEXICON)
        # dhamma has untranslated_preferred=True, so it stays as-is in the output
        self.assertEqual(result.translated, "dhamma")
        self.assertEqual(result.unknown_tokens, [])
        # The term IS recorded in matches (as a successful lookup)
        self.assertEqual(len(result.matches), 1)
        self.assertTrue(result.matches[0].untranslated_preferred)

    def test_unknown_words_reported(self):
        result = translate_text("dukkha zzunknown", LEXICON)
        self.assertEqual(result.unknown_tokens, ["zzunknown"])

    def test_original_preserved(self):
        text = "dukkha nibbana"
        result = translate_text(text, LEXICON)
        self.assertEqual(result.original, text)

    def test_punctuation_stripped_for_lookup(self):
        result = translate_text("dukkha, nibbana.", LEXICON)
        # Tokens with surrounding punctuation should still resolve
        self.assertIn("dissatisfaction", result.translated)
        self.assertIn("unbinding", result.translated)

    def test_empty_input(self):
        result = translate_text("", LEXICON)
        self.assertEqual(result.translated, "")
        self.assertEqual(result.matches, [])
        self.assertEqual(result.unknown_tokens, [])

    def test_only_punctuation_is_preserved_and_not_marked_unknown(self):
        result = translate_text("dukkha --- nibbana", LEXICON)
        self.assertEqual(result.translated, "dissatisfaction --- unbinding")
        self.assertEqual(result.unknown_tokens, [])

    def test_unknown_tokens_preserve_order(self):
        result = translate_text("zzone dukkha zztwo", LEXICON)
        self.assertEqual(result.unknown_tokens, ["zzone", "zztwo"])

    def test_missing_record_fields_fall_back_cleanly(self):
        sparse = Lexicon.from_dict({
            "sati": {
                "term": "sati",
                "normalized_term": "sati",
            }
        })
        match = lookup_term("sati", sparse)
        self.assertIsNotNone(match)
        self.assertEqual(match.preferred_translation, "sati")
        self.assertEqual(match.alternative_translations, [])
        self.assertEqual(match.definition, "")
        self.assertEqual(match.entry_type, "")


class TestNormalizeConsistency(unittest.TestCase):
    """Verify that lexicon._normalize and translator._normalize stay in sync.

    Both modules intentionally duplicate the normalisation logic so they can
    be imported independently.  This test catches any future drift between the
    two copies.
    """

    _FIXTURES = [
        "dukkha",
        "Dukkha",
        "nibbāna",
        "non-ill-will",
        "noble truth",
        "Sīla",
        "ĀNĀPĀNASATI",
        "",
    ]

    def test_outputs_match(self):
        for term in self._FIXTURES:
            with self.subTest(term=term):
                self.assertEqual(lex_normalize(term), tr_normalize(term))


if __name__ == "__main__":
    unittest.main()
