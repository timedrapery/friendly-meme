"""Application controller for the Pāli translator GUI.

Separates all business logic from the Tk presentation layer.
No tkinter imports here — this module is safe to import and test in a
headless (display-less) environment.

Typical lifecycle
-----------------
1. Instantiate: ``ctrl = Controller()``
2. Load lexicon — may block on a cold cache (call from a background thread):
   ``status = ctrl.load_lexicon()``
3. Translate text or look up individual terms:
   ``result = ctrl.translate(text)``
   ``match  = ctrl.lookup("dukkha")``
4. Inspect the session for export:
   ``session = ctrl.current_session``
5. Browse history:
   ``sessions = ctrl.history.get_all()``
6. Work with concordance, filter, notes, and comparison via the helper
   methods documented below.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from ..lexicon import Lexicon
from ..phrases import PhraseMatch, match_phrases
from ..translator import (
    TermMatch,
    TranslationResult,
    _normalize,
    _tokenize,
    lookup_term,
    translate_text,
)
from .compare import ComparisonSummary, compare_sessions
from .concordance import ConcordanceEntry, build_concordance
from .history import HistoryStore
from .notes import NotesStore
from .settings import AppSettings


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class LexiconStatus:
    """Snapshot of lexicon load state surfaced in the GUI status bar."""

    loaded: bool = False
    from_cache: bool = False
    cache_path: str = ""
    entry_count: int = 0
    error: str = ""


@dataclass
class TokenRow:
    """Per-token analysis row displayed in the workbench table.

    Every whitespace-separated token from the source passage gets one row,
    regardless of whether it was found in the lexicon.
    """

    token: str
    normalized: str
    matched: bool
    preferred_translation: str
    entry_type: str
    untranslated_preferred: bool
    definition: str
    alternatives: list[str] = field(default_factory=list)


@dataclass
class TranslationSession:
    """One user translation pass — source text + full results + metadata.

    Captured after every :meth:`Controller.translate` call and used by the
    export layer to serialize a complete session record.
    """

    source_text: str
    result: TranslationResult
    token_rows: list[TokenRow]
    lexicon_status: LexiconStatus
    phrase_matches: list[PhraseMatch] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )


# ---------------------------------------------------------------------------
# Filter helpers (pure functions — testable without a Controller instance)
# ---------------------------------------------------------------------------

FilterMode = Literal["all", "unknown", "matched", "policy"]


def filter_tokens(
    rows: list[TokenRow],
    text: str = "",
    mode: FilterMode = "all",
) -> list[TokenRow]:
    """Return the subset of *rows* that satisfies *text* and *mode* filters.

    Parameters
    ----------
    rows:
        Full list of token rows from a session.
    text:
        Free-text substring filter applied to the token, normalized form,
        preferred translation, and definition fields (case-insensitive).
        An empty string disables text filtering.
    mode:
        Category filter:

        ``"all"``
            No category filter — return everything (after text filter).
        ``"unknown"``
            Only rows where ``matched`` is ``False``.
        ``"matched"``
            Only rows where ``matched`` is ``True``.
        ``"policy"``
            Only rows where ``untranslated_preferred`` is ``True``.

    Returns
    -------
    list[TokenRow]
        Filtered rows, preserving original order.
    """
    result: list[TokenRow] = rows

    if mode == "unknown":
        result = [r for r in result if not r.matched]
    elif mode == "matched":
        result = [r for r in result if r.matched]
    elif mode == "policy":
        result = [r for r in result if r.untranslated_preferred]

    if text:
        needle = text.lower()
        result = [
            r for r in result
            if (
                needle in r.token.lower()
                or needle in r.normalized.lower()
                or needle in r.preferred_translation.lower()
                or needle in r.definition.lower()
            )
        ]

    return result


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------

class Controller:
    """Mediates between the GUI and the translation engine.

    All methods that interact with the lexicon or translator are pure Python;
    the GUI is responsible for threading and UI updates.
    """

    def __init__(self) -> None:
        self._lexicon: Lexicon | None = None
        self._status = LexiconStatus()
        self._session: TranslationSession | None = None

        # Sprint 3/4 state
        self._settings: AppSettings = AppSettings.load()
        self._history: HistoryStore = HistoryStore(
            maxlen=self._settings.history_size
        )
        self._notes: NotesStore = NotesStore()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def lexicon_ready(self) -> bool:
        """Return ``True`` when the lexicon is loaded and ready for queries."""
        return self._lexicon is not None

    @property
    def status(self) -> LexiconStatus:
        """Return the current lexicon load-state snapshot."""
        return self._status

    @property
    def current_session(self) -> TranslationSession | None:
        """Return the most recent translation session, or ``None``."""
        return self._session

    @property
    def settings(self) -> AppSettings:
        """Return the current application settings."""
        return self._settings

    @property
    def history(self) -> HistoryStore:
        """Return the passage history store."""
        return self._history

    @property
    def notes(self) -> NotesStore:
        """Return the notes store for the current session."""
        return self._notes

    # ------------------------------------------------------------------
    # Lexicon management
    # ------------------------------------------------------------------

    def load_lexicon(
        self,
        refresh: bool = False,
        cache_path: Path | str | None = None,
    ) -> LexiconStatus:
        """Load the lexicon from cache or GitHub.

        This call may take tens of seconds when the cache does not exist (it
        will download term records from GitHub).  It is designed to be called
        from a background thread; ``self._status`` is updated atomically so
        the GUI can read it after the call completes.

        Parameters
        ----------
        refresh:
            When ``True``, ignore any existing cache and re-download from
            GitHub.
        cache_path:
            Override the default cache location.

        Returns
        -------
        LexiconStatus
            Updated status snapshot after the load attempt.
        """
        resolved = Path(cache_path) if cache_path else None
        try:
            lex = Lexicon(cache_path=resolved, refresh=refresh)
            self._lexicon = lex
            self._status = LexiconStatus(
                loaded=True,
                from_cache=lex.loaded_from_cache,
                cache_path=str(lex.cache_path),
                entry_count=len(lex),
            )
        except RuntimeError as exc:
            self._status = LexiconStatus(loaded=False, error=str(exc))
        return self._status

    # ------------------------------------------------------------------
    # Translation and lookup
    # ------------------------------------------------------------------

    def translate(self, text: str) -> TranslationResult:
        """Translate *text*, record the session, and return the result.

        The new session is pushed to the history store and the notes store
        is reset so it is ready for fresh annotations.

        Raises
        ------
        RuntimeError
            When no lexicon has been loaded yet.
        """
        if self._lexicon is None:
            raise RuntimeError(
                "Lexicon is not loaded yet. Please wait for the lexicon to finish loading."
            )
        result = translate_text(text, self._lexicon)
        rows = self._build_token_rows(text)
        tokens = _tokenize(text)
        phrases = match_phrases(tokens, self._lexicon)
        self._session = TranslationSession(
            source_text=text,
            result=result,
            token_rows=rows,
            lexicon_status=self._status,
            phrase_matches=phrases,
        )
        self._history.add(self._session)
        self._notes.clear_all()
        return result

    def restore_session(self, session: TranslationSession) -> None:
        """Restore a past session as the current session.

        This does **not** re-translate — the session object is used as-is.
        Notes are *not* cleared, so any current annotations survive; the
        caller is responsible for managing that if needed.
        """
        self._session = session

    def lookup(self, term: str) -> TermMatch | None:
        """Look up a single Pāli term in the lexicon.

        Raises
        ------
        RuntimeError
            When no lexicon has been loaded yet.
        """
        if self._lexicon is None:
            raise RuntimeError("Lexicon is not loaded yet.")
        return lookup_term(term, self._lexicon)

    # ------------------------------------------------------------------
    # Concordance
    # ------------------------------------------------------------------

    def build_concordance(
        self,
        sort_mode: str | None = None,
    ) -> list[ConcordanceEntry]:
        """Build a concordance from the current session's token rows.

        Parameters
        ----------
        sort_mode:
            One of ``"frequency"``, ``"alpha"``, ``"appearance"``.
            Defaults to the value in :attr:`settings`.

        Returns
        -------
        list[ConcordanceEntry]
            Empty list when there is no current session.
        """
        if self._session is None:
            return []
        mode = sort_mode or self._settings.concordance_sort
        return build_concordance(self._session.token_rows, sort_mode=mode)

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def filter_session_tokens(
        self,
        text: str = "",
        mode: FilterMode = "all",
    ) -> list[TokenRow]:
        """Filter the current session's token rows.

        Returns an empty list when there is no current session.
        """
        if self._session is None:
            return []
        return filter_tokens(self._session.token_rows, text=text, mode=mode)

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    def compare(
        self,
        session_a: TranslationSession,
        session_b: TranslationSession,
    ) -> ComparisonSummary:
        """Compare two sessions and return a structured diff."""
        return compare_sessions(session_a, session_b)

    # ------------------------------------------------------------------
    # Settings persistence
    # ------------------------------------------------------------------

    def save_settings(self) -> None:
        """Persist current settings to disk."""
        self._settings.save()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_token_rows(self, text: str) -> list[TokenRow]:
        """Build per-token analysis rows for the workbench display table.

        Mirrors the tokenisation logic of :func:`~pali_translator.translator.translate_text`
        so that table rows match the translated output exactly.
        """
        assert self._lexicon is not None  # guaranteed by callers
        rows: list[TokenRow] = []
        for token in _tokenize(text):
            word = token.strip(".,;:!?\"'()[]{}—-")
            if not word:
                continue
            match = lookup_term(word, self._lexicon)
            normalized = _normalize(word)
            if match is not None:
                rows.append(
                    TokenRow(
                        token=token,
                            normalized=normalized,
                        matched=True,
                        preferred_translation=match.preferred_translation,
                        entry_type=match.entry_type,
                        untranslated_preferred=match.untranslated_preferred,
                        definition=match.definition,
                        alternatives=match.alternative_translations,
                    )
                )
            else:
                rows.append(
                    TokenRow(
                        token=token,
                        normalized=normalized,
                        matched=False,
                        preferred_translation="",
                        entry_type="",
                        untranslated_preferred=False,
                        definition="",
                        alternatives=[],
                    )
                )
        return rows
