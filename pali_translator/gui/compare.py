"""Translation comparison for the Pāli translator workbench.

Two :class:`~pali_translator.gui.controller.TranslationSession` objects
can be compared to produce a :class:`ComparisonSummary` that highlights:

* tokens that appear in one passage but not the other,
* tokens whose preferred translation differs between sessions,
* tokens that changed match status (unknown → matched or vice-versa).

Usage
-----
::

    summary = compare_sessions(session_a, session_b)
    for diff in summary.changed_tokens:
        print(diff.normalized, diff.old_translation, "→", diff.new_translation)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .controller import TranslationSession


@dataclass
class TokenDiff:
    """A token whose preferred translation changed between two sessions.

    Attributes
    ----------
    normalized:
        Canonical form of the token.
    old_translation:
        Preferred translation in session A (``None`` if absent).
    new_translation:
        Preferred translation in session B (``None`` if absent).
    """

    normalized: str
    old_translation: str | None
    new_translation: str | None


@dataclass
class ComparisonSummary:
    """Structured diff between two translation sessions.

    Attributes
    ----------
    session_a_timestamp:
        ISO timestamp of the first (older / base) session.
    session_b_timestamp:
        ISO timestamp of the second (newer) session.
    added_tokens:
        Normalised tokens present in session B but not in session A.
    removed_tokens:
        Normalised tokens present in session A but not in session B.
    changed_tokens:
        Tokens present in both sessions whose preferred translation differs.
    newly_matched:
        Tokens that were *unknown* in session A but *matched* in session B.
        (Implies the lexicon was refreshed or the token was corrected.)
    newly_unknown:
        Tokens that were *matched* in session A but *unknown* in session B.
    """

    session_a_timestamp: str
    session_b_timestamp: str
    added_tokens: list[str] = field(default_factory=list)
    removed_tokens: list[str] = field(default_factory=list)
    changed_tokens: list[TokenDiff] = field(default_factory=list)
    newly_matched: list[str] = field(default_factory=list)
    newly_unknown: list[str] = field(default_factory=list)

    @property
    def has_differences(self) -> bool:
        """Return ``True`` when any meaningful difference was detected."""
        return bool(
            self.added_tokens
            or self.removed_tokens
            or self.changed_tokens
            or self.newly_matched
            or self.newly_unknown
        )


def compare_sessions(
    session_a: "TranslationSession",
    session_b: "TranslationSession",
) -> ComparisonSummary:
    """Compare *session_a* (base) with *session_b* (target).

    The comparison is vocabulary-level — it looks at the set of unique
    *normalised* tokens in each session and the preferred translation
    attached to each.  Repetition of the same token within a session does
    not influence the diff; only the vocabulary matters.

    Parameters
    ----------
    session_a:
        The base/reference session.
    session_b:
        The new/target session to compare against *session_a*.

    Returns
    -------
    ComparisonSummary
        Structured diff result.
    """
    # Build normalised-token → row maps (last row wins for duplicates, which
    # should not occur in well-formed sessions but is handled defensively).
    def _index(session: "TranslationSession") -> dict[str, object]:
        return {row.normalized: row for row in session.token_rows}

    rows_a = _index(session_a)
    rows_b = _index(session_b)

    keys_a = set(rows_a)
    keys_b = set(rows_b)

    added = sorted(keys_b - keys_a)
    removed = sorted(keys_a - keys_b)

    changed: list[TokenDiff] = []
    newly_matched: list[str] = []
    newly_unknown: list[str] = []

    for key in sorted(keys_a & keys_b):
        row_a = rows_a[key]  # type: ignore[union-attr]
        row_b = rows_b[key]  # type: ignore[union-attr]

        # Match-status changes.
        if not row_a.matched and row_b.matched:  # type: ignore[union-attr]
            newly_matched.append(key)
        elif row_a.matched and not row_b.matched:  # type: ignore[union-attr]
            newly_unknown.append(key)

        # Translation changes (only meaningful for matched tokens).
        trans_a = row_a.preferred_translation if row_a.matched else None  # type: ignore[union-attr]
        trans_b = row_b.preferred_translation if row_b.matched else None  # type: ignore[union-attr]
        if trans_a != trans_b:
            changed.append(
                TokenDiff(
                    normalized=key,
                    old_translation=trans_a,
                    new_translation=trans_b,
                )
            )

    return ComparisonSummary(
        session_a_timestamp=session_a.timestamp,
        session_b_timestamp=session_b.timestamp,
        added_tokens=added,
        removed_tokens=removed,
        changed_tokens=changed,
        newly_matched=newly_matched,
        newly_unknown=newly_unknown,
    )
