"""Tests for the Pali-to-contemporary-English translator."""

from __future__ import annotations

import unittest

from pali_translator.lexicon import Lexicon, _normalize
from pali_translator.translator import lookup_term, translate_text


# ---------------------------------------------------------------------------
# Minimal synthetic lexicon used across all tests (no network access needed)
# ---------------------------------------------------------------------------

_SAMPLE_RECORDS = {
    "dukkha": {
        "term": "dukkha",
        "normalized_term": "dukkha",
        "entry_type": "major",
        "part_of_speech": "noun",
        "preferred_translation": "dissatisfaction",
        "alternative_translations": ["unsatisfactoriness", "stress"],
        "discouraged_translations": ["suffering"],
        "definition": "The unstable and unsatisfactory character of conditioned experience.",
        "untranslated_preferred": False,
        "status": "stable",
    },
    "nibbana": {
        "term": "nibbāna",
        "normalized_term": "nibbana",
        "entry_type": "major",
        "part_of_speech": "noun",
        "preferred_translation": "unbinding",
        "alternative_translations": ["liberation"],
        "discouraged_translations": ["nirvana"],
        "definition": "The cessation of clinging and the fires of passion.",
        "untranslated_preferred": False,
        "status": "stable",
    },
    "dhamma": {
        "term": "dhamma",
        "normalized_term": "dhamma",
        "entry_type": "major",
        "part_of_speech": "noun",
        "preferred_translation": "dhamma",
        "alternative_translations": [],
        "definition": "The teaching; the nature of things.",
        "untranslated_preferred": True,
        "status": "stable",
    },
    "ajiva": {
        "term": "ajiva",
        "normalized_term": "ajiva",
        "entry_type": "minor",
        "part_of_speech": "noun",
        "preferred_translation": "livelihood",
        "definition": "A speech, path, or conduct term used in ethical and practical analysis.",
        "untranslated_preferred": False,
        "status": "reviewed",
    },
}

LEXICON = Lexicon.from_dict(_SAMPLE_RECORDS)


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


class TestLexiconLookup(unittest.TestCase):
    def test_lookup_known_term(self):
        record = LEXICON.lookup("dukkha")
        self.assertIsNotNone(record)
        self.assertEqual(record["preferred_translation"], "dissatisfaction")

    def test_lookup_diacritic_variant(self):
        record = LEXICON.lookup("nibbāna")
        # The sample index key is 'nibbana'; diacritics should be stripped on lookup
        self.assertIsNotNone(record)
        self.assertEqual(record["preferred_translation"], "unbinding")

    def test_lookup_case_insensitive(self):
        record = LEXICON.lookup("Dukkha")
        self.assertIsNotNone(record)

    def test_lookup_unknown_returns_none(self):
        self.assertIsNone(LEXICON.lookup("zzunknown"))

    def test_len(self):
        self.assertEqual(len(LEXICON), len(_SAMPLE_RECORDS))

    def test_contains(self):
        self.assertIn("dukkha", LEXICON)
        self.assertNotIn("zzunknown", LEXICON)


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


if __name__ == "__main__":
    unittest.main()
