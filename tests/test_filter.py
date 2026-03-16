"""Tests for pali_translator.gui.controller.filter_tokens — token filtering."""

from __future__ import annotations

import unittest

from pali_translator.gui.controller import TokenRow, filter_tokens


def _row(token: str, matched: bool = True, preferred: str = "p",
         untranslated: bool = False, definition: str = "def") -> TokenRow:
    return TokenRow(
        token=token,
        normalized=token.lower(),
        matched=matched,
        preferred_translation=preferred,
        entry_type="major" if matched else "",
        untranslated_preferred=untranslated,
        definition=definition,
        alternatives=[],
    )


ALL_ROWS = [
    _row("dukkha",  matched=True,  preferred="dissatisfaction"),
    _row("nibbana", matched=True,  preferred="unbinding"),
    _row("dhamma",  matched=True,  preferred="dhamma",  untranslated=True),
    _row("xyz",     matched=False, preferred=""),
    _row("abc",     matched=False, preferred=""),
]


class TestFilterAll(unittest.TestCase):
    def test_mode_all_returns_everything(self):
        result = filter_tokens(ALL_ROWS, mode="all")
        self.assertEqual(len(result), 5)

    def test_empty_text_no_filter(self):
        result = filter_tokens(ALL_ROWS, text="", mode="all")
        self.assertEqual(len(result), 5)


class TestFilterMode(unittest.TestCase):
    def test_mode_unknown_returns_unknowns(self):
        result = filter_tokens(ALL_ROWS, mode="unknown")
        self.assertTrue(all(not r.matched for r in result))
        self.assertEqual(len(result), 2)

    def test_mode_matched_returns_matched(self):
        result = filter_tokens(ALL_ROWS, mode="matched")
        self.assertTrue(all(r.matched for r in result))
        self.assertEqual(len(result), 3)

    def test_mode_policy_returns_untranslated_preferred(self):
        result = filter_tokens(ALL_ROWS, mode="policy")
        self.assertTrue(all(r.untranslated_preferred for r in result))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].token, "dhamma")

    def test_mode_all_with_no_text_same_as_all(self):
        result = filter_tokens(ALL_ROWS, text="", mode="all")
        self.assertEqual(len(result), len(ALL_ROWS))


class TestFilterText(unittest.TestCase):
    def test_text_filter_on_token(self):
        result = filter_tokens(ALL_ROWS, text="dukkha")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].token, "dukkha")

    def test_text_filter_case_insensitive(self):
        result = filter_tokens(ALL_ROWS, text="DUKKHA")
        self.assertEqual(len(result), 1)

    def test_text_filter_on_preferred_translation(self):
        result = filter_tokens(ALL_ROWS, text="unbinding")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].token, "nibbana")

    def test_text_filter_combined_with_mode(self):
        rows = ALL_ROWS + [_row("nibbana2", matched=False)]
        result = filter_tokens(rows, text="nibbana", mode="unknown")
        # Only unknown rows containing "nibbana"
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].token, "nibbana2")

    def test_text_filter_no_match_returns_empty(self):
        result = filter_tokens(ALL_ROWS, text="zzznomatch")
        self.assertEqual(result, [])

    def test_text_filter_on_definition(self):
        rows = [_row("test", definition="the nature of existence")]
        result = filter_tokens(rows, text="nature")
        self.assertEqual(len(result), 1)

    def test_empty_rows_returns_empty(self):
        self.assertEqual(filter_tokens([],"dukkha"), [])

    def test_preserves_order(self):
        result = filter_tokens(ALL_ROWS, mode="matched")
        tokens = [r.token for r in result]
        self.assertEqual(tokens, ["dukkha", "nibbana", "dhamma"])


if __name__ == "__main__":
    unittest.main()
