"""Interlinear reading model for the Pāli translator workbench.

An *interlinear* view displays each token together with its gloss (preferred
translation) directly above or below it, in the manner of classical interlinear
Bible or Pāli textbook editions.  Multi-word phrase matches are represented as
a single grouped unit so the reader sees the phrase-level meaning as well as
the individual word analysis.

Usage
-----
::

    units = build_interlinear(session.token_rows, phrase_matches)
    for unit in units:
        print(unit.token, "–", unit.gloss)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .controller import TokenRow
    from ..phrases import PhraseMatch


@dataclass
class InterlinearUnit:
    """One display cell in the interlinear reading view.

    A unit corresponds to a single token *or* is the opening cell of a
    multi-word phrase (in which case ``is_phrase_start`` is ``True`` and
    ``phrase_rendering`` carries the whole-phrase gloss).

    Attributes
    ----------
    token:
        Surface form from the passage.
    normalized:
        Canonical form used for lexicon lookups.
    gloss:
        Preferred translation (``preferred_translation`` for matched tokens,
        ``"???"`` for unknowns).  For policy-kept terms the Pāli form
        itself is used as the gloss.
    entry_type:
        Lexicon entry type string, or ``""`` for unknowns.
    untranslated_preferred:
        ``True`` when the term is kept in Pāli by editorial policy.
    matched:
        ``True`` when the token was found in the lexicon.
    is_phrase_start:
        ``True`` when this unit is the first token of a phrase match.
    is_phrase_end:
        ``True`` when this unit is the last token of a phrase match.
    phrase_rendering:
        The full phrase's preferred translation if ``is_phrase_start`` is
        ``True``, otherwise ``None``.
    phrase_span:
        The full tuple of tokens forming the phrase if this is a phrase
        start, otherwise ``None``.
    """

    token: str
    normalized: str
    gloss: str
    entry_type: str
    untranslated_preferred: bool
    matched: bool
    is_phrase_start: bool = False
    is_phrase_end: bool = False
    phrase_rendering: str | None = None
    phrase_span: tuple[str, ...] | None = None


def build_interlinear(
    token_rows: list["TokenRow"],
    phrase_matches: list["PhraseMatch"],
) -> list[InterlinearUnit]:
    """Build an interlinear unit list from *token_rows* and *phrase_matches*.

    Each element of *token_rows* becomes exactly one :class:`InterlinearUnit`.
    Phrase boundary information is attached to the units that fall within a
    matched phrase so the presentation layer can render phrase groupings.

    Parameters
    ----------
    token_rows:
        Per-token rows from the current session.
    phrase_matches:
        List of phrase matches for the same passage, as returned by
        :func:`~pali_translator.phrases.match_phrases`.

    Returns
    -------
    list[InterlinearUnit]
        One unit per token, in passage order.
    """
    # Index phrase matches by start and end position for O(1) lookup.
    phrase_starts: dict[int, "PhraseMatch"] = {}
    phrase_ends: set[int] = set()
    phrase_member_positions: set[int] = set()

    for pm in phrase_matches:
        phrase_starts[pm.start_pos] = pm
        phrase_ends.add(pm.end_pos - 1)  # last token index (inclusive)
        for i in range(pm.start_pos, pm.end_pos):
            phrase_member_positions.add(i)

    units: list[InterlinearUnit] = []
    for pos, row in enumerate(token_rows):
        # Determine gloss
        if row.matched:
            gloss = row.preferred_translation or row.token
        else:
            gloss = "???"

        # Phrase boundary flags
        is_start = pos in phrase_starts
        is_end = pos in phrase_ends
        pm = phrase_starts.get(pos)

        units.append(
            InterlinearUnit(
                token=row.token,
                normalized=row.normalized,
                gloss=gloss,
                entry_type=row.entry_type,
                untranslated_preferred=row.untranslated_preferred,
                matched=row.matched,
                is_phrase_start=is_start,
                is_phrase_end=is_end,
                phrase_rendering=pm.preferred_rendering if pm else None,
                phrase_span=pm.span if pm else None,
            )
        )

    return units
