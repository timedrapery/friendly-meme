"""Editorial notes store for the Pāli translator workbench.

Three tiers of notes are supported per session:

session note
    Free-text commentary on the passage as a whole.
token notes
    Per-term annotations keyed by the normalised token form.
phrase notes
    Per-phrase annotations keyed by a human-readable span string
    (the normalised tokens joined with ``"_"``).

Notes are kept in memory alongside the current workbench session.  The
:mod:`~pali_translator.gui.export` layer can include them in JSON and
Markdown exports.

Usage
-----
::

    store = NotesStore()
    store.set_session_note("This passage is from MN 36.")
    store.set_token_note("dukkha", "compare ajahn chah's rendering")
    store.to_dict()  # → serialisable dict for export
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class NotesStore:
    """Container for all editorial notes attached to a workbench session.

    Attributes
    ----------
    session_note:
        Free-text note for the passage as a whole.
    token_notes:
        Dict mapping normalised token form → note text.
    phrase_notes:
        Dict mapping span key (normalised tokens joined with ``"_"``) → note.
    """

    session_note: str = ""
    token_notes: dict[str, str] = field(default_factory=dict)
    phrase_notes: dict[str, str] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Session-level
    # ------------------------------------------------------------------

    def set_session_note(self, note: str) -> None:
        """Set the passage-level note (replaces any existing content)."""
        self.session_note = note

    def clear_session_note(self) -> None:
        """Clear the passage-level note."""
        self.session_note = ""

    # ------------------------------------------------------------------
    # Token-level
    # ------------------------------------------------------------------

    def set_token_note(self, normalized: str, note: str) -> None:
        """Attach *note* to the normalised token *normalized*.

        An empty *note* string removes the entry.
        """
        if note:
            self.token_notes[normalized] = note
        else:
            self.token_notes.pop(normalized, None)

    def get_token_note(self, normalized: str) -> str:
        """Return the note for *normalized*, or ``""`` if none."""
        return self.token_notes.get(normalized, "")

    def clear_token_note(self, normalized: str) -> None:
        """Remove the note for *normalized* (no-op if absent)."""
        self.token_notes.pop(normalized, None)

    # ------------------------------------------------------------------
    # Phrase-level
    # ------------------------------------------------------------------

    @staticmethod
    def span_key(normalized_span: tuple[str, ...] | list[str]) -> str:
        """Convert a normalised token tuple into a storage key string."""
        return "_".join(normalized_span)

    def set_phrase_note(self, span_key: str, note: str) -> None:
        """Attach *note* to the phrase identified by *span_key*.

        An empty *note* removes the entry.
        """
        if note:
            self.phrase_notes[span_key] = note
        else:
            self.phrase_notes.pop(span_key, None)

    def get_phrase_note(self, span_key: str) -> str:
        """Return the note for *span_key*, or ``""`` if none."""
        return self.phrase_notes.get(span_key, "")

    def clear_phrase_note(self, span_key: str) -> None:
        """Remove the note for *span_key* (no-op if absent)."""
        self.phrase_notes.pop(span_key, None)

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def clear_all(self) -> None:
        """Remove all notes (session, token, and phrase)."""
        self.session_note = ""
        self.token_notes.clear()
        self.phrase_notes.clear()

    def is_empty(self) -> bool:
        """Return ``True`` when no notes of any kind have been written."""
        return (
            not self.session_note
            and not self.token_notes
            and not self.phrase_notes
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Return a plain-Python representation suitable for JSON export."""
        return {
            "session_note": self.session_note,
            "token_notes": dict(self.token_notes),
            "phrase_notes": dict(self.phrase_notes),
        }
