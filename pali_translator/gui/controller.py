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
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ..lexicon import Lexicon
from ..translator import (
    TermMatch,
    TranslationResult,
    _normalize,
    _tokenize,
    lookup_term,
    translate_text,
)


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
    timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )


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
        self._session = TranslationSession(
            source_text=text,
            result=result,
            token_rows=rows,
            lexicon_status=self._status,
        )
        return result

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
