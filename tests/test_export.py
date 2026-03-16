"""Tests for translation session export / report generation.

Covers both :func:`~pali_translator.gui.export.export_json` and
:func:`~pali_translator.gui.export.export_plain_text` by building a fixture
session and asserting on the serialized output — no network or display needed.
"""

from __future__ import annotations

import json
import unittest

from pali_translator.gui.controller import LexiconStatus, TokenRow, TranslationSession
from pali_translator.gui.export import export_json, export_plain_text
from pali_translator.translator import TermMatch, TranslationResult


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

def _make_session(*, from_cache: bool = True) -> TranslationSession:
    """Build a minimal but realistic TranslationSession for testing."""
    matches = [
        TermMatch(
            token="dukkha",
            preferred_translation="dissatisfaction",
            alternative_translations=["unsatisfactoriness", "stress"],
            definition="The unstable and unsatisfactory character of conditioned experience.",
            entry_type="major",
            untranslated_preferred=False,
        ),
        TermMatch(
            token="dhamma",
            preferred_translation="dhamma",
            alternative_translations=[],
            definition="The teaching; the nature of things. A Pāli term kept untranslated by policy.",
            entry_type="major",
            untranslated_preferred=True,
        ),
    ]
    result = TranslationResult(
        original="dukkha dhamma zzunk",
        translated="dissatisfaction dhamma zzunk",
        matches=matches,
        unknown_tokens=["zzunk"],
    )
    rows = [
        TokenRow(
            token="dukkha",
            normalized="dukkha",
            matched=True,
            preferred_translation="dissatisfaction",
            entry_type="major",
            untranslated_preferred=False,
            definition="The unstable and unsatisfactory character of conditioned experience.",
            alternatives=["unsatisfactoriness", "stress"],
        ),
        TokenRow(
            token="dhamma",
            normalized="dhamma",
            matched=True,
            preferred_translation="dhamma",
            entry_type="major",
            untranslated_preferred=True,
            definition="The teaching; the nature of things. A Pāli term kept untranslated by policy.",
            alternatives=[],
        ),
        TokenRow(
            token="zzunk",
            normalized="zzunk",
            matched=False,
            preferred_translation="",
            entry_type="",
            untranslated_preferred=False,
            definition="",
            alternatives=[],
        ),
    ]
    status = LexiconStatus(
        loaded=True,
        from_cache=from_cache,
        cache_path="/fake/lexicon.json",
        entry_count=42,
    )
    return TranslationSession(
        source_text="dukkha dhamma zzunk",
        result=result,
        token_rows=rows,
        lexicon_status=status,
        timestamp="2026-03-16T12:00:00",
    )


# ---------------------------------------------------------------------------
# JSON export tests
# ---------------------------------------------------------------------------

class TestExportJson(unittest.TestCase):
    def setUp(self) -> None:
        self.session = _make_session()
        self.raw = export_json(self.session)
        self.data = json.loads(self.raw)

    def test_is_valid_json(self) -> None:
        # setUp would have raised on bad JSON
        self.assertIsInstance(self.data, dict)

    def test_source_text_preserved(self) -> None:
        self.assertEqual(self.data["source_text"], "dukkha dhamma zzunk")

    def test_translated_text_present(self) -> None:
        self.assertEqual(self.data["translated_text"], "dissatisfaction dhamma zzunk")

    def test_timestamp_correct(self) -> None:
        self.assertEqual(self.data["timestamp"], "2026-03-16T12:00:00")

    def test_lexicon_source_cache(self) -> None:
        self.assertEqual(self.data["lexicon_source"], "cache")

    def test_lexicon_source_network(self) -> None:
        session = _make_session(from_cache=False)
        data = json.loads(export_json(session))
        self.assertEqual(data["lexicon_source"], "network")

    def test_cache_path_included(self) -> None:
        self.assertEqual(self.data["cache_path"], "/fake/lexicon.json")

    def test_matches_list_length(self) -> None:
        self.assertEqual(len(self.data["matches"]), 2)

    def test_match_fields_present(self) -> None:
        m = self.data["matches"][0]
        self.assertEqual(m["token"], "dukkha")
        self.assertEqual(m["preferred_translation"], "dissatisfaction")
        self.assertIn("unsatisfactoriness", m["alternative_translations"])
        self.assertFalse(m["untranslated_preferred"])
        self.assertEqual(m["entry_type"], "major")

    def test_untranslated_preferred_flag_in_match(self) -> None:
        dhamma_match = next(m for m in self.data["matches"] if m["token"] == "dhamma")
        self.assertTrue(dhamma_match["untranslated_preferred"])

    def test_unknown_tokens_included(self) -> None:
        self.assertIn("zzunk", self.data["unknown_tokens"])

    def test_counts_correct(self) -> None:
        self.assertEqual(self.data["match_count"],   2)
        self.assertEqual(self.data["unknown_count"], 1)
        self.assertEqual(self.data["token_count"],   3)

    def test_unicode_preserved(self) -> None:
        # Pāli diacritics and Unicode in the output must survive round-tripping.
        self.assertIn("Pāli", self.raw)

    def test_output_is_indented(self) -> None:
        # Should be pretty-printed (indent=2).
        self.assertIn("\n  ", self.raw)


# ---------------------------------------------------------------------------
# Plain-text export tests
# ---------------------------------------------------------------------------

class TestExportPlainText(unittest.TestCase):
    def setUp(self) -> None:
        self.session = _make_session()
        self.text = export_plain_text(self.session)

    def test_contains_report_header(self) -> None:
        self.assertIn("Pāli Translation Report", self.text)

    def test_contains_timestamp(self) -> None:
        self.assertIn("2026-03-16T12:00:00", self.text)

    def test_contains_source_section(self) -> None:
        self.assertIn("SOURCE", self.text)
        self.assertIn("dukkha dhamma zzunk", self.text)

    def test_contains_translation_section(self) -> None:
        self.assertIn("TRANSLATION", self.text)
        self.assertIn("dissatisfaction", self.text)

    def test_contains_token_analysis_section(self) -> None:
        self.assertIn("TOKEN ANALYSIS", self.text)

    def test_kept_in_pali_marker_present(self) -> None:
        self.assertIn("kept in Pāli", self.text)

    def test_not_in_lexicon_marker_present(self) -> None:
        self.assertIn("NOT IN LEXICON", self.text)
        self.assertIn("zzunk", self.text)

    def test_unknown_tokens_section_present(self) -> None:
        self.assertIn("UNKNOWN TOKENS", self.text)

    def test_lexicon_source_cache_label(self) -> None:
        self.assertIn("cache", self.text)

    def test_lexicon_source_network_label(self) -> None:
        session = _make_session(from_cache=False)
        text = export_plain_text(session)
        self.assertIn("network", text)

    def test_entry_type_included(self) -> None:
        self.assertIn("major", self.text)

    def test_definition_included(self) -> None:
        self.assertIn("unstable and unsatisfactory", self.text)

    def test_alternatives_included(self) -> None:
        self.assertIn("unsatisfactoriness", self.text)

    def test_entry_count_included(self) -> None:
        self.assertIn("42", self.text)

    def test_no_session_unknown_tokens_no_unknown_section(self) -> None:
        """When there are no unknowns the UNKNOWN TOKENS section should not appear."""
        from pali_translator.translator import TranslationResult, TermMatch
        result = TranslationResult(
            original="dukkha",
            translated="dissatisfaction",
            matches=[
                TermMatch(
                    token="dukkha",
                    preferred_translation="dissatisfaction",
                    entry_type="major",
                    untranslated_preferred=False,
                )
            ],
            unknown_tokens=[],
        )
        from pali_translator.gui.controller import TokenRow
        rows = [
            TokenRow(
                token="dukkha", normalized="dukkha", matched=True,
                preferred_translation="dissatisfaction", entry_type="major",
                untranslated_preferred=False, definition="", alternatives=[],
            )
        ]
        status = LexiconStatus(
            loaded=True, from_cache=True, cache_path="/x", entry_count=1,
        )
        session = TranslationSession(
            source_text="dukkha",
            result=result,
            token_rows=rows,
            lexicon_status=status,
            timestamp="2026-01-01T00:00:00",
        )
        text = export_plain_text(session)
        self.assertNotIn("UNKNOWN TOKENS", text)
