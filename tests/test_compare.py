"""Tests for pali_translator.gui.compare — TokenDiff + compare_sessions."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from pali_translator.gui.compare import TokenDiff, ComparisonSummary, compare_sessions
from pali_translator.gui.controller import LexiconStatus, TokenRow, TranslationSession
from pali_translator.translator import TranslationResult


def _session(tokens: list[tuple], timestamp: datetime | None = None) -> TranslationSession:
    """Build a minimal TranslationSession from a list of (token, preferred, matched) tuples."""
    rows = []
    for t in tokens:
        token, preferred, matched = t
        rows.append(
            TokenRow(
                token=token,
                normalized=token.lower(),
                matched=matched,
                preferred_translation=preferred,
                entry_type="major" if matched else "",
                untranslated_preferred=False,
                definition="",
                alternatives=[],
            )
        )
    ts = timestamp.isoformat() if timestamp else "2024-01-01T00:00:00"
    return TranslationSession(
        source_text="example pali source",
        result=TranslationResult(
            original="example pali source",
            translated=" ".join(r.preferred_translation for r in rows),
            matches=[],
            unknown_tokens=[],
        ),
        token_rows=rows,
        lexicon_status=LexiconStatus(loaded=True, from_cache=True, cache_path="", entry_count=0),
        timestamp=ts,
    )


class TestCompareIdentical(unittest.TestCase):
    def test_no_diff_on_identical_sessions(self):
        s = _session([("dukkha", "suffering", True), ("nibbana", "cessation", True)])
        summary = compare_sessions(s, s)
        self.assertFalse(summary.has_differences)

    def test_added_and_removed_empty(self):
        s = _session([("dukkha", "suffering", True)])
        summary = compare_sessions(s, s)
        self.assertEqual(summary.added_tokens, [])
        self.assertEqual(summary.removed_tokens, [])

    def test_changed_empty(self):
        s = _session([("dukkha", "suffering", True)])
        summary = compare_sessions(s, s)
        self.assertEqual(summary.changed_tokens, [])


class TestAddedTokens(unittest.TestCase):
    def test_token_in_b_not_a_is_added(self):
        a = _session([("dukkha", "suffering", True)])
        b = _session([("dukkha", "suffering", True), ("nibbana", "cessation", True)])
        summary = compare_sessions(a, b)
        self.assertIn("nibbana", summary.added_tokens)

    def test_added_not_in_removed(self):
        a = _session([("dukkha", "suffering", True)])
        b = _session([("dukkha", "suffering", True), ("nibbana", "cessation", True)])
        summary = compare_sessions(a, b)
        self.assertNotIn("nibbana", summary.removed_tokens)

    def test_has_differences_true_when_added(self):
        a = _session([("dukkha", "suffering", True)])
        b = _session([("dukkha", "suffering", True), ("nibbana", "cessation", True)])
        self.assertTrue(compare_sessions(a, b).has_differences)


class TestRemovedTokens(unittest.TestCase):
    def test_token_in_a_not_b_is_removed(self):
        a = _session([("dukkha", "suffering", True), ("nibbana", "cessation", True)])
        b = _session([("dukkha", "suffering", True)])
        summary = compare_sessions(a, b)
        self.assertIn("nibbana", summary.removed_tokens)

    def test_removed_not_in_added(self):
        a = _session([("dukkha", "suffering", True), ("nibbana", "cessation", True)])
        b = _session([("dukkha", "suffering", True)])
        summary = compare_sessions(a, b)
        self.assertNotIn("nibbana", summary.added_tokens)


class TestChangedTokens(unittest.TestCase):
    def test_different_translation_is_changed(self):
        a = _session([("dukkha", "suffering", True)])
        b = _session([("dukkha", "dissatisfaction", True)])
        summary = compare_sessions(a, b)
        self.assertEqual(len(summary.changed_tokens), 1)
        diff = summary.changed_tokens[0]
        self.assertEqual(diff.normalized, "dukkha")
        self.assertEqual(diff.old_translation, "suffering")
        self.assertEqual(diff.new_translation, "dissatisfaction")

    def test_same_translation_not_changed(self):
        a = _session([("dukkha", "suffering", True)])
        b = _session([("dukkha", "suffering", True)])
        summary = compare_sessions(a, b)
        self.assertEqual(summary.changed_tokens, [])

    def test_has_differences_true_when_changed(self):
        a = _session([("dukkha", "suffering", True)])
        b = _session([("dukkha", "dissatisfaction", True)])
        self.assertTrue(compare_sessions(a, b).has_differences)


class TestNewlyMatchedAndUnknown(unittest.TestCase):
    def test_newly_matched(self):
        a = _session([("dukkha", "", False)])
        b = _session([("dukkha", "suffering", True)])
        summary = compare_sessions(a, b)
        self.assertIn("dukkha", summary.newly_matched)

    def test_newly_unknown(self):
        a = _session([("dukkha", "suffering", True)])
        b = _session([("dukkha", "", False)])
        summary = compare_sessions(a, b)
        self.assertIn("dukkha", summary.newly_unknown)

    def test_always_matched_not_newly_matched(self):
        a = _session([("dukkha", "suffering", True)])
        b = _session([("dukkha", "dissatisfaction", True)])
        summary = compare_sessions(a, b)
        self.assertNotIn("dukkha", summary.newly_matched)


class TestTimestamps(unittest.TestCase):
    def test_timestamps_preserved(self):
        t1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2024, 6, 1, tzinfo=timezone.utc)
        a = _session([("dukkha", "suffering", True)], timestamp=t1)
        b = _session([("dukkha", "suffering", True)], timestamp=t2)
        summary = compare_sessions(a, b)
        self.assertEqual(summary.session_a_timestamp, t1.isoformat())
        self.assertEqual(summary.session_b_timestamp, t2.isoformat())


class TestEmptySessions(unittest.TestCase):
    def test_both_empty_no_diff(self):
        a = _session([])
        b = _session([])
        summary = compare_sessions(a, b)
        self.assertFalse(summary.has_differences)

    def test_a_empty_b_has_tokens(self):
        a = _session([])
        b = _session([("dukkha", "suffering", True)])
        summary = compare_sessions(a, b)
        self.assertIn("dukkha", summary.added_tokens)
        self.assertTrue(summary.has_differences)


if __name__ == "__main__":
    unittest.main()
