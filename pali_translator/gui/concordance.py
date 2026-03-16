"""Concordance builder for the Pāli translator workbench.

A concordance groups every unique *normalised* token from the current session
by its lexicon entry, reporting how often each occurs and which translation
applies.  This lets the reader quickly audit which terms dominate a passage.

Usage
-----
::

    entries = build_concordance(session.token_rows, sort_mode="frequency")
    # → list[ConcordanceEntry], sorted by descending occurrence count.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .controller import TokenRow


@dataclass
class ConcordanceEntry:
    """One unique (normalised) term as it appears in a passage.

    Attributes
    ----------
    normalized:
        The canonical form used as the lookup key.
    representative_token:
        An example surface form (first occurrence) for display purposes.
    count:
        Number of times the normalised form appeared in the passage.
    preferred_translation:
        Preferred rendering from the lexicon, or ``""`` for unknowns.
    entry_type:
        Lexicon entry type (e.g. ``"major"``, ``"minor"``), or ``""``.
    untranslated_preferred:
        ``True`` when the policy keeps the term in Pāli.
    matched:
        ``True`` when the term was found in the lexicon.
    first_position:
        Zero-based index of the *first* token row where this term appeared.
        Used for "appearance" sort order.
    """

    normalized: str
    representative_token: str
    count: int
    preferred_translation: str
    entry_type: str
    untranslated_preferred: bool
    matched: bool
    first_position: int = 0


_VALID_SORT_MODES = {"frequency", "alpha", "appearance"}


def build_concordance(
    token_rows: list["TokenRow"],
    sort_mode: str = "frequency",
) -> list[ConcordanceEntry]:
    """Build a concordance from *token_rows*.

    Parameters
    ----------
    token_rows:
        Rows produced by :meth:`~pali_translator.gui.controller.Controller.translate`.
    sort_mode:
        How to order the result list:

        ``"frequency"``
            Most-frequent normalised forms first; alphabetical for ties.
        ``"alpha"``
            Strict alphabetical order on the normalised form.
        ``"appearance"``
            Order of first appearance in the passage.

    Returns
    -------
    list[ConcordanceEntry]
        One entry per unique normalised form.

    Raises
    ------
    ValueError
        When *sort_mode* is not one of the recognised values.
    """
    if sort_mode not in _VALID_SORT_MODES:
        raise ValueError(
            f"sort_mode must be one of {sorted(_VALID_SORT_MODES)!r}, got {sort_mode!r}"
        )

    # First pass: accumulate data keyed by normalised form.
    seen: dict[str, ConcordanceEntry] = {}
    for pos, row in enumerate(token_rows):
        key = row.normalized
        if key in seen:
            seen[key].count += 1
        else:
            seen[key] = ConcordanceEntry(
                normalized=key,
                representative_token=row.token,
                count=1,
                preferred_translation=row.preferred_translation,
                entry_type=row.entry_type,
                untranslated_preferred=row.untranslated_preferred,
                matched=row.matched,
                first_position=pos,
            )

    entries = list(seen.values())

    if sort_mode == "frequency":
        entries.sort(key=lambda e: (-e.count, e.normalized))
    elif sort_mode == "alpha":
        entries.sort(key=lambda e: e.normalized)
    else:  # "appearance"
        entries.sort(key=lambda e: e.first_position)

    return entries
