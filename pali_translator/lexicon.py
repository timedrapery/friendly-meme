"""Lexicon loader for the shiny-adventure Pāli term database.

Responsibilities
----------------
* Fetch all ``terms/major/*.json`` and ``terms/minor/*.json`` files from the
  ``timedrapery/shiny-adventure`` GitHub repository via the git-tree API and
  raw-content URLs.
* Build an in-memory lookup index keyed by the ASCII-normalised form of each
  Pāli headword (diacritics stripped, lower-cased, non-alphanumeric characters
  collapsed to underscores).
* Persist the assembled index to a local JSON cache so subsequent runs are
  fast and work offline.
* Expose a :class:`Lexicon` class with a simple ``lookup(term)`` interface.

Authentication
--------------
By default, requests are unauthenticated (GitHub allows ~60 API calls/hour).
Set the ``GITHUB_TOKEN`` environment variable to a personal access token to
raise that limit to ~5 000 calls/hour — useful when the cache does not yet
exist and hundreds of term files need to be downloaded in one session.

Cache location
--------------
``~/.cache/pali_translator/lexicon.json``

Override by passing ``cache_path`` to :class:`Lexicon`.  Pass
``refresh=True`` to force a fresh download even when the cache exists.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Repository coordinates
# ---------------------------------------------------------------------------

REPO_OWNER = "timedrapery"
REPO_NAME = "shiny-adventure"
REPO_REF = "main"  # branch or tag to fetch from

# GitHub git-tree API endpoint — ?recursive=1 returns the entire file tree in
# one request so we don't have to traverse directories individually.
_GITHUB_TREE_URL = (
    f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
    f"/git/trees/{REPO_REF}?recursive=1"
)

# Base URL for raw file content (no API rate-limit overhead for file bodies).
_RAW_BASE = (
    f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{REPO_REF}"
)

# Default location for the assembled lexicon cache.
DEFAULT_CACHE_PATH = Path.home() / ".cache" / "pali_translator" / "lexicon.json"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _auth_headers() -> dict[str, str]:
    """Return HTTP request headers, injecting a Bearer token when available.

    If the ``GITHUB_TOKEN`` environment variable is set its value is added as
    an ``Authorization`` header, which raises the GitHub API rate limit from
    60 to 5 000 requests per hour.
    """
    headers: dict[str, str] = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "pali-translator",
    }
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def _fetch_json(url: str) -> Any:
    """Perform an authenticated GET request and parse the JSON response body.

    Raises :class:`RuntimeError` with a human-readable hint when the server
    returns HTTP 403 (typically a GitHub rate-limit response).  All other HTTP
    errors are re-raised as-is.
    """
    req = urllib.request.Request(url, headers=_auth_headers())
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            raise RuntimeError(
                "GitHub API returned 403. You may be hitting the unauthenticated "
                "rate limit. Set the GITHUB_TOKEN environment variable to a "
                "personal access token to increase the limit."
            ) from exc
        raise


def _normalize(term: str) -> str:
    """Return the canonical ASCII-lowercase key used to index the lexicon.

    Steps:
    1. NFKD-decompose the string so that combined characters are split into
       base + combining mark sequences.
    2. Drop all combining marks (diacritics), leaving only base characters.
    3. Lower-case the result.
    4. Replace any run of non-alphanumeric characters with a single underscore
       and strip leading/trailing underscores.

    Examples::

        _normalize("nibbāna")   # → "nibbana"
        _normalize("Dukkha")    # → "dukkha"
        _normalize("non-ill-will")  # → "non_ill_will"
    """
    normalized = unicodedata.normalize("NFKD", term)
    stripped = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    lowered = stripped.lower()
    return re.sub(r"[^a-z0-9]+", "_", lowered).strip("_")


def _fetch_lexicon_from_github() -> dict[str, dict]:
    """Download every term JSON file from shiny-adventure and build the index.

    Algorithm
    ---------
    1. Fetch the git-tree for the repository root (recursive) — one API call.
    2. Filter the tree to entries whose path starts with ``terms/`` and ends
       with ``.json`` (i.e., term records; schema and other JSON files are
       ignored because they live outside ``terms/``).
    3. Fetch each file's raw content from ``raw.githubusercontent.com`` (not
       counted against the API rate limit).
    4. Index each record by its ``normalized_term`` field.  Also add a second
       entry keyed by the diacritic-normalised form of the display ``term``
       field when it differs, so callers can look up with or without diacritics.

    Returns
    -------
    dict[str, dict]
        Mapping from normalised key → raw record dict.
    """
    tree_data = _fetch_json(_GITHUB_TREE_URL)

    # Collect paths for all term JSON files; skip directories and other blobs.
    term_paths = [
        entry["path"]
        for entry in tree_data.get("tree", [])
        if entry.get("path", "").startswith("terms/")
        and entry["path"].endswith(".json")
        and entry.get("type") == "blob"
    ]

    lexicon: dict[str, dict] = {}
    for path in term_paths:
        url = f"{_RAW_BASE}/{path}"
        try:
            req = urllib.request.Request(url, headers=_auth_headers())
            with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
                record = json.loads(resp.read().decode())
        except (urllib.error.URLError, json.JSONDecodeError):
            # Skip individual files that fail — a partial lexicon is still
            # useful and avoids aborting a large download on transient errors.
            continue

        # Primary key: use the explicit normalized_term field when present;
        # fall back to deriving it from the display term.
        key = record.get("normalized_term") or _normalize(record.get("term", ""))
        if not key:
            continue

        lexicon[key] = record

        # Secondary key: the diacritic-normalised display term, when it
        # differs from normalized_term, so lookups with diacritics resolve too.
        display_key = _normalize(record.get("term", ""))
        if display_key and display_key != key:
            lexicon[display_key] = record

    return lexicon


# ---------------------------------------------------------------------------
# Public class
# ---------------------------------------------------------------------------

class Lexicon:
    """In-memory Pāli lexicon loaded from the shiny-adventure repository.

    The first time a :class:`Lexicon` is instantiated (or when ``refresh=True``
    is passed) the full term database is downloaded from GitHub and written to
    a local JSON cache.  Subsequent instantiations read from that cache, so
    they are fast and work offline.

    Parameters
    ----------
    cache_path:
        Override the default cache location
        (``~/.cache/pali_translator/lexicon.json``).
    refresh:
        When ``True``, ignore any existing cache and re-fetch from GitHub.

    Examples
    --------
    Basic usage::

        lexicon = Lexicon()
        record  = lexicon.lookup("dukkha")
        print(record["preferred_translation"])  # "dissatisfaction"

    Inject a pre-built dict for testing::

        lexicon = Lexicon.from_dict({"dukkha": {...}})
    """

    def __init__(self, cache_path: Path | None = None, refresh: bool = False) -> None:
        self._cache_path = Path(cache_path) if cache_path else DEFAULT_CACHE_PATH
        self._index: dict[str, dict] = {}
        self._load(refresh=refresh)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def lookup(self, term: str) -> dict | None:
        """Return the lexicon record for *term*, or ``None`` if not found.

        Lookup is case-insensitive and diacritic-insensitive: both
        ``"Dukkha"`` and ``"dukkha"`` resolve to the same entry, as do
        ``"nibbāna"`` and ``"nibbana"``.
        """
        return self._index.get(_normalize(term))

    def __len__(self) -> int:
        """Return the number of indexed keys (not unique records)."""
        return len(self._index)

    def __contains__(self, term: str) -> bool:
        """Support ``term in lexicon`` membership tests."""
        return _normalize(term) in self._index

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self, *, refresh: bool) -> None:
        """Populate ``self._index`` from cache or GitHub."""
        if not refresh and self._cache_path.exists():
            # Fast path: read the pre-built index from disk.
            with self._cache_path.open(encoding="utf-8") as fh:
                self._index = json.load(fh)
            return

        # Slow path: download from GitHub and persist the result.
        self._index = _fetch_lexicon_from_github()
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self._cache_path.open("w", encoding="utf-8") as fh:
            json.dump(self._index, fh, ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, dict]) -> "Lexicon":
        """Create a :class:`Lexicon` directly from *data* without hitting disk or
        the network.

        Intended for unit tests that need a predictable, offline lexicon.

        Parameters
        ----------
        data:
            Mapping from normalised Pāli key → term record dict.  The keys
            should already be in the same normalised form produced by
            :func:`_normalize`.
        """
        instance = cls.__new__(cls)
        instance._cache_path = Path("/dev/null")  # never written
        instance._index = data
        return instance
