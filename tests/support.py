"""Shared test fixtures for pali_translator unit tests."""

from __future__ import annotations

from pali_translator.lexicon import Lexicon


SAMPLE_RECORDS = {
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


def make_lexicon() -> Lexicon:
    """Return an in-memory lexicon populated with sample term records."""
    return Lexicon.from_dict(SAMPLE_RECORDS)