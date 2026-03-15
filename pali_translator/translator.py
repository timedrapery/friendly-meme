"""Core translation logic for Pāli-to-contemporary-English lookup.

Public interface
----------------
lookup_term(term, lexicon) → TermMatch | None
    Look up a single Pāli word.  Returns a :class:`TermMatch` dataclass
    populated from the lexicon record, or ``None`` when the word is not found.

translate_text(text, lexicon) → TranslationResult
    Tokenise *text*, look up each token, and substitute the preferred
    contemporary English rendering for every known term.  Unknown tokens are
    left as-is.  Returns a :class:`TranslationResult` carrying the translated
    passage, a list of resolved :class:`TermMatch` objects, and a list of
    unresolved token strings.

Translation policy
------------------
* If a term's record carries ``untranslated_preferred: true`` the token is
  left in Pāli in the output, but the match IS still recorded so callers can
  see that the word was found and intentionally not translated.
* Surrounding punctuation (commas, periods, etc.) is stripped before lookup
  but re-attached in the translated output so prose punctuation is preserved.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Imported at type-check time only to avoid a circular import at runtime;
    # translator.py is imported by cli.py which also imports lexicon.py.
    from .lexicon import Lexicon


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TermMatch:
    """A single resolved match between a Pāli input token and a lexicon entry.

    Attributes
    ----------
    token:
        The original Pāli word as it appeared in the input (before any
        punctuation stripping).
    preferred_translation:
        The OSF-governed preferred English rendering.  When
        ``untranslated_preferred`` is ``True`` this holds the Pāli term itself
        (the token is intentionally kept in Pāli).
    alternative_translations:
        Acceptable alternate renderings documented in the lexicon entry.
    definition:
        Short explanatory definition from the lexicon record.
    entry_type:
        ``"major"`` or ``"minor"`` — indicates the editorial weight of the
        entry (major entries carry full translation policy; minor entries are
        lighter reference records).
    untranslated_preferred:
        ``True`` when the lexicon policy is to leave the term in Pāli rather
        than substitute an English word.
    """

    token: str
    preferred_translation: str
    alternative_translations: list[str] = field(default_factory=list)
    definition: str = ""
    entry_type: str = ""
    untranslated_preferred: bool = False


@dataclass
class TranslationResult:
    """The result of translating a Pāli passage.

    Attributes
    ----------
    original:
        The unchanged input text.
    translated:
        The passage with every known, translatable term replaced by its
        preferred English rendering.
    matches:
        All terms that were found in the lexicon, including those kept in Pāli
        due to ``untranslated_preferred`` policy.
    unknown_tokens:
        Words that were not found in the lexicon at all.  These are left
        verbatim in ``translated`` and surfaced here so callers can decide
        what to do with them.
    """

    original: str
    translated: str
    matches: list[TermMatch] = field(default_factory=list)
    unknown_tokens: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalize(term: str) -> str:
    """Return the ASCII-lowercase normalised form used for lexicon lookups.

    Mirrors the normalisation logic in :mod:`pali_translator.lexicon` so that
    input tokens and index keys always use the same canonical form.
    """
    nfkd = unicodedata.normalize("NFKD", term)
    stripped = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "_", stripped.lower()).strip("_")


def _tokenize(text: str) -> list[str]:
    """Split *text* on whitespace, returning one token per non-space run.

    Punctuation attached to a word (``"dukkha,"`` or ``"nibbāna."``) is kept
    as part of the token; :func:`lookup_term` strips it before the lexicon
    lookup and restores it in the output.
    """
    return re.findall(r"[^\s]+", text)


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def lookup_term(term: str, lexicon: "Lexicon") -> TermMatch | None:
    """Look up a single Pāli term in *lexicon*.

    Parameters
    ----------
    term:
        A Pāli word (may include diacritics; lookup is normalised).
    lexicon:
        A loaded :class:`~pali_translator.lexicon.Lexicon` instance.

    Returns
    -------
    TermMatch
        Populated from the matching lexicon record.
    None
        When the term is not present in the lexicon.
    """
    record = lexicon.lookup(term)
    if record is None:
        return None

    untranslated = record.get("untranslated_preferred", False)
    return TermMatch(
        token=term,
        # When the policy says "leave in Pāli", surface the display term from
        # the record (preserving diacritics) rather than any English gloss.
        preferred_translation=(
            record.get("term", term) if untranslated
            else record.get("preferred_translation", term)
        ),
        alternative_translations=record.get("alternative_translations", []),
        definition=record.get("definition", ""),
        entry_type=record.get("entry_type", ""),
        untranslated_preferred=untranslated,
    )


def translate_text(text: str, lexicon: "Lexicon") -> TranslationResult:
    """Translate a Pāli passage by replacing known terms with preferred English.

    Each whitespace-separated token is looked up in the lexicon after stripping
    leading/trailing punctuation.  Known terms are substituted; unknown tokens
    are passed through unchanged.

    Terms marked ``untranslated_preferred: true`` in the lexicon are kept in
    Pāli in the output (per OSF editorial policy) but are still recorded in
    the ``matches`` list so callers know the token was recognised.

    Parameters
    ----------
    text:
        A Pāli passage, possibly containing a mix of Pāli words and other text.
    lexicon:
        A loaded :class:`~pali_translator.lexicon.Lexicon` instance.

    Returns
    -------
    TranslationResult
        Contains the translated text plus per-token match and unknown-token
        metadata.
    """
    tokens = _tokenize(text)
    translated_tokens: list[str] = []
    matches: list[TermMatch] = []
    unknown: list[str] = []

    for token in tokens:
        # Strip surrounding punctuation for the lookup, then reattach it in
        # the output so that prose punctuation ("dukkha,") is preserved.
        word = token.strip(".,;:!?\"'()[]{}—-")
        match = lookup_term(word, lexicon) if word else None

        if match is not None:
            # Term found: substitute English (or keep Pāli if policy says so).
            if not match.untranslated_preferred:
                translated_tokens.append(token.replace(word, match.preferred_translation, 1))
            else:
                translated_tokens.append(token)  # intentionally left in Pāli
            matches.append(match)
        else:
            # Term not in lexicon: pass through unchanged and record it.
            translated_tokens.append(token)
            if word:
                unknown.append(word)

    return TranslationResult(
        original=text,
        translated=" ".join(translated_tokens),
        matches=matches,
        unknown_tokens=unknown,
    )
