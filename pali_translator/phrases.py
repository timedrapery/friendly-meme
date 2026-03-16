"""Multi-word phrase matching for the Pāli translator.

Lexicon entries whose ``term`` field contains whitespace (e.g. ``"bodhi
citta"``) or whose ``normalized_term`` contains underscores (e.g.
``"bodhi_citta"``) are treated as phrase candidates.  Given a list of tokens
from a passage, :func:`match_phrases` finds all such candidates using a
**longest-match-first**, **non-overlapping** scan.

This module lives in the core layer (``pali_translator/``) and has no
Tkinter dependency.  It is called by the GUI controller and is independently
testable.

Usage
-----
::

    tokens = ["bodhi", "citta", "is", "dukkha"]
    matches = match_phrases(tokens, lexicon)
    # matches[0].span == ("bodhi", "citta"), matches[0].start_pos == 0
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .lexicon import Lexicon


_MAX_PHRASE_LEN = 6   # maximum tokens in a recognized phrase
_MIN_PHRASE_LEN = 2   # at least two tokens to count as a phrase


def _normalize(term: str) -> str:
    """Reproduce the same normalisation as :func:`pali_translator.translator._normalize`."""
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", term)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    lowered = stripped.lower()
    return re.sub(r"[^\w]", "_", lowered)


@dataclass
class PhraseMatch:
    """A multi-word Pāli phrase identified in a token stream.

    Attributes
    ----------
    span:
        Tuple of surface-form tokens from the passage.
    normalized_span:
        Tuple of normalised tokens used for the lookup key.
    start_pos:
        Zero-based index of the first token in the original token list.
    end_pos:
        Zero-based index *one past* the last token (exclusive), matching
        Python slice semantics.
    preferred_rendering:
        Preferred translation for the whole phrase from the lexicon.
    entry_type:
        Lexicon entry type (e.g. ``"major"``); empty string if absent.
    untranslated_preferred:
        ``True`` when the lexicon policy keeps the phrase in Pāli.
    source_key:
        The ``normalized_term`` key that matched this phrase in the lexicon.
    """

    span: tuple[str, ...]
    normalized_span: tuple[str, ...]
    start_pos: int
    end_pos: int
    preferred_rendering: str
    entry_type: str
    untranslated_preferred: bool
    source_key: str


def _build_phrase_index(lexicon: "Lexicon") -> dict[tuple[str, ...], dict]:
    """Extract all multi-word entries from *lexicon* into a lookup index.

    The index maps a tuple of normalised tokens  →  the full lexicon record.
    Only entries with 2–6 words are included.
    """
    index: dict[tuple[str, ...], dict] = {}
    for key, record in lexicon.items():
        # Two code-paths to discover phrase entries:
        #   1. normalized_term contains underscores (primary)
        #   2. term field contains whitespace (fallback)
        normalized_term: str = record.get("normalized_term", key)
        if "_" in normalized_term:
            parts = tuple(normalized_term.split("_"))
        else:
            term_text: str = record.get("term", "")
            if " " not in term_text:
                continue
            parts = tuple(_normalize(t) for t in term_text.split())

        if _MIN_PHRASE_LEN <= len(parts) <= _MAX_PHRASE_LEN:
            index[parts] = record
    return index


def match_phrases(
    tokens: list[str],
    lexicon: "Lexicon",
) -> list[PhraseMatch]:
    """Find all multi-word phrase matches in *tokens* using *lexicon*.

    The scan is **longest-match-first** and **non-overlapping**: once a span
    is claimed by a longer match, its tokens cannot be claimed again.

    Parameters
    ----------
    tokens:
        Raw whitespace-separated tokens from the passage (as produced by
        :func:`~pali_translator.translator._tokenize`).  Punctuation is
        stripped from each token before normalisation.
    lexicon:
        Loaded :class:`~pali_translator.lexicon.Lexicon` instance.

    Returns
    -------
    list[PhraseMatch]
        Phrase matches in order of appearance (by ``start_pos``).
    """
    if not tokens:
        return []

    phrase_index = _build_phrase_index(lexicon)
    if not phrase_index:
        return []

    # Strip punctuation from each token to get the word core used for lookup.
    cleaned = [t.strip(".,;:!?\"'()[]{}—-") for t in tokens]
    normalized = [_normalize(w) if w else "" for w in cleaned]

    n = len(tokens)
    matched: list[PhraseMatch] = []
    # Track which positions are already consumed by a match.
    consumed = [False] * n

    for start in range(n):
        if consumed[start]:
            continue

        best: PhraseMatch | None = None

        # Try longest phrases first so we always prefer longer matches.
        max_end = min(start + _MAX_PHRASE_LEN, n) + 1
        for end in range(max_end, start + _MIN_PHRASE_LEN - 1, -1):
            if end > n:
                continue
            # Skip if any token in this span is already consumed.
            if any(consumed[i] for i in range(start, end)):
                continue
            span_norm = tuple(normalized[start:end])
            # Skip spans that contain empty strings (punctuation-only tokens).
            if any(s == "" for s in span_norm):
                continue
            record = phrase_index.get(span_norm)
            if record is not None:
                best = PhraseMatch(
                    span=tuple(tokens[start:end]),
                    normalized_span=span_norm,
                    start_pos=start,
                    end_pos=end,
                    preferred_rendering=record.get("preferred_translation", ""),
                    entry_type=record.get("entry_type", ""),
                    untranslated_preferred=bool(
                        record.get("untranslated_preferred", False)
                    ),
                    source_key=record.get("normalized_term", "_".join(span_norm)),
                )
                break  # longest match found for this start position

        if best is not None:
            matched.append(best)
            for i in range(best.start_pos, best.end_pos):
                consumed[i] = True

    return matched
