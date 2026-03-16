"""Passage history store for the Pāli translator workbench.

Keeps the last *N* :class:`~pali_translator.gui.controller.TranslationSession`
objects in a bounded in-memory deque.  The cap defaults to 25 and can be
changed at runtime (useful when the user edits their settings).

Usage
-----
::

    store = HistoryStore(maxlen=25)
    store.add(session)
    all_sessions = store.get_all()   # most-recent first
    # restore a session by simply reading it — nothing to "restore" in the
    # store itself; the caller re-populates the UI from the returned object.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .controller import TranslationSession


class HistoryStore:
    """Bounded in-memory store for past translation sessions.

    Parameters
    ----------
    maxlen:
        Maximum number of sessions to retain (oldest are dropped first).
        Must be at least 1.
    """

    def __init__(self, maxlen: int = 25) -> None:
        if maxlen < 1:
            raise ValueError(f"maxlen must be >= 1, got {maxlen!r}")
        self._maxlen = maxlen
        self._sessions: deque["TranslationSession"] = deque(maxlen=maxlen)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def maxlen(self) -> int:
        """Current capacity (maximum number of sessions retained)."""
        return self._maxlen

    @maxlen.setter
    def maxlen(self, value: int) -> None:
        """Resize the store.  Excess oldest entries are dropped when shrinking."""
        if value < 1:
            raise ValueError(f"maxlen must be >= 1, got {value!r}")
        self._maxlen = value
        # Rebuild with new capacity, preserving most-recent entries.
        new_deque: deque["TranslationSession"] = deque(maxlen=value)
        # _sessions[0] is oldest; we want to keep the newest ones.
        for session in list(self._sessions)[-value:]:
            new_deque.append(session)
        self._sessions = new_deque

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add(self, session: "TranslationSession") -> None:
        """Append *session* to the store.  Oldest entry dropped when full."""
        self._sessions.append(session)

    def clear(self) -> None:
        """Remove all sessions from the store."""
        self._sessions.clear()

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_all(self) -> list["TranslationSession"]:
        """Return all sessions, most-recent first."""
        return list(reversed(self._sessions))

    def get(self, index: int) -> "TranslationSession":
        """Return session at *index* in most-recent-first order.

        Raises
        ------
        IndexError
            When *index* is out of range.
        """
        sessions = self.get_all()
        return sessions[index]

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._sessions)

    def __bool__(self) -> bool:
        return bool(self._sessions)
