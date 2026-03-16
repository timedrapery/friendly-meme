"""Tests for pali_translator.gui.concordance — ConcordanceEntry + build_concordance."""

from __future__ import annotations

import unittest

from pali_translator.gui.concordance import ConcordanceEntry, build_concordance
from pali_translator.gui.controller import TokenRow


def _row(token: str, normalized: str, matched: bool, preferred: str = "",
         entry_type: str = "", untranslated: bool = False) -> TokenRow:
    return TokenRow(
        token=token,
        normalized=normalized,
        matched=matched,
        preferred_translation=preferred,
        entry_type=entry_type,
        untranslated_preferred=untranslated,
        definition="",
        alternatives=[],
    )


_ROWS = [
    _row("dukkha",  "dukkha",  True,  "dissatisfaction", "major"),
    _row("dukkha",  "dukkha",  True,  "dissatisfaction", "major"),
    _row("nibbana", "nibbana", True,  "unbinding",        "major"),
    _row("dukkha",  "dukkha",  True,  "dissatisfaction", "major"),
    _row("ajiva",   "ajiva",   True,  "livelihood",       "minor"),
    _row("xyz",     "xyz",     False, ""),
]


class TestBuildConcordance(unittest.TestCase):
    def test_returns_list_of_concordance_entries(self):
        result = build_concordance(_ROWS)
        self.assertIsInstance(result, list)
        self.assertTrue(all(isinstance(e, ConcordanceEntry) for e in result))

    def test_unique_normalised_forms(self):
        result = build_concordance(_ROWS)
        normalised = [e.normalized for e in result]
        self.assertEqual(len(normalised), len(set(normalised)))

    def test_correct_counts(self):
        result = build_concordance(_ROWS)
        counts = {e.normalized: e.count for e in result}
        self.assertEqual(counts["dukkha"], 3)
        self.assertEqual(counts["nibbana"], 1)
        self.assertEqual(counts["xyz"], 1)

    def test_frequency_sort_order(self):
        result = build_concordance(_ROWS, sort_mode="frequency")
        self.assertEqual(result[0].normalized, "dukkha")

    def test_alpha_sort_order(self):
        result = build_concordance(_ROWS, sort_mode="alpha")
        normalised = [e.normalized for e in result]
        self.assertEqual(normalised, sorted(normalised))

    def test_appearance_sort_order(self):
        result = build_concordance(_ROWS, sort_mode="appearance")
        # dukkha appears first, then nibbana, then ajiva, then xyz
        self.assertEqual(result[0].normalized, "dukkha")
        self.assertEqual(result[1].normalized, "nibbana")

    def test_invalid_sort_mode_raises(self):
        with self.assertRaises(ValueError):
            build_concordance(_ROWS, sort_mode="nonsense")

    def test_unknown_token_included(self):
        result = build_concordance(_ROWS)
        norms = {e.normalized for e in result}
        self.assertIn("xyz", norms)
        xyz = next(e for e in result if e.normalized == "xyz")
        self.assertFalse(xyz.matched)

    def test_matched_flag_correct(self):
        result = build_concordance(_ROWS)
        dukkha = next(e for e in result if e.normalized == "dukkha")
        self.assertTrue(dukkha.matched)

    def test_preferred_translation_preserved(self):
        result = build_concordance(_ROWS)
        dukkha = next(e for e in result if e.normalized == "dukkha")
        self.assertEqual(dukkha.preferred_translation, "dissatisfaction")

    def test_empty_rows_returns_empty(self):
        self.assertEqual(build_concordance([]), [])

    def test_policy_flag(self):
        rows = [_row("dhamma", "dhamma", True, "dhamma", "major", untranslated=True)]
        result = build_concordance(rows)
        self.assertTrue(result[0].untranslated_preferred)

    def test_frequency_ties_broken_alphabetically(self):
        rows = [
            _row("aaa", "aaa", True, "a"),
            _row("bbb", "bbb", True, "b"),
        ]
        result = build_concordance(rows, sort_mode="frequency")
        # Both count=1; alphabetical tiebreak.
        self.assertEqual(result[0].normalized, "aaa")

    def test_representative_token_is_first_occurrence(self):
        result = build_concordance(_ROWS)
        dukkha = next(e for e in result if e.normalized == "dukkha")
        self.assertEqual(dukkha.representative_token, "dukkha")

    def test_first_position_tracked(self):
        result = build_concordance(_ROWS, sort_mode="appearance")
        positions = {e.normalized: e.first_position for e in result}
        self.assertEqual(positions["dukkha"], 0)
        self.assertEqual(positions["nibbana"], 2)
        self.assertEqual(positions["ajiva"], 4)


if __name__ == "__main__":
    unittest.main()
