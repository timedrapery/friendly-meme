"""Core translation logic for Pali-to-contemporary-English lookup."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .lexicon import Lexicon


@dataclass
class TermMatch:
    """A single resolved match between a Pali token and a lexicon entry."""

    token: str
    preferred_translation: str
    alternative_translations: list[str] = field(default_factory=list)
    definition: str = ""
    entry_type: str = ""
    untranslated_preferred: bool = False


@dataclass
class TranslationResult:
    """The result of translating a Pali passage."""

    original: str
    translated: str
    matches: list[TermMatch] = field(default_factory=list)
    unknown_tokens: list[str] = field(default_factory=list)


def _normalize(term: str) -> str:
    """Return the ASCII-lowercase normalized form used for lookups."""
    nfkd = unicodedata.normalize("NFKD", term)
    stripped = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "_", stripped.lower()).strip("_")


def _tokenize(text: str) -> list[str]:
    """Split *text* into Pali word tokens, preserving punctuation tokens separately."""
    return re.findall(r"[^\s]+", text)


def lookup_term(term: str, lexicon: "Lexicon") -> TermMatch | None:
    """Look up a single Pali term in *lexicon*.

    Returns a :class:`TermMatch` if found, or ``None``.
    """
    record = lexicon.lookup(term)
    if record is None:
        return None
    untranslated = record.get("untranslated_preferred", False)
    return TermMatch(
        token=term,
        preferred_translation=record.get("term") if untranslated else record.get("preferred_translation", term),
        alternative_translations=record.get("alternative_translations", []),
        definition=record.get("definition", ""),
        entry_type=record.get("entry_type", ""),
        untranslated_preferred=untranslated,
    )


def translate_text(text: str, lexicon: "Lexicon") -> TranslationResult:
    """Translate a Pali passage by replacing each known term with its preferred
    contemporary English rendering.

    Tokens whose normalized form is not found in the lexicon are left as-is.
    A summary of resolved matches and unresolved tokens is attached to the
    returned :class:`TranslationResult`.
    """
    tokens = _tokenize(text)
    translated_tokens: list[str] = []
    matches: list[TermMatch] = []
    unknown: list[str] = []

    for token in tokens:
        # Strip surrounding punctuation before lookup
        word = token.strip(".,;:!?\"'()[]{}—-")
        match = lookup_term(word, lexicon) if word else None
        if match and not match.untranslated_preferred:
            translated_tokens.append(
                token.replace(word, match.preferred_translation, 1)
            )
            matches.append(match)
        elif match and match.untranslated_preferred:
            translated_tokens.append(token)
            matches.append(match)
        else:
            translated_tokens.append(token)
            if word and match is None:
                unknown.append(word)

    return TranslationResult(
        original=text,
        translated=" ".join(translated_tokens),
        matches=matches,
        unknown_tokens=unknown,
    )
