"""Lexicon loader: fetches and caches the shiny-adventure Pali term data from GitHub."""

from __future__ import annotations

import json
import os
import re
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO_OWNER = "timedrapery"
REPO_NAME = "shiny-adventure"
REPO_REF = "main"

_GITHUB_TREE_URL = (
    f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
    f"/git/trees/{REPO_REF}?recursive=1"
)
_RAW_BASE = (
    f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{REPO_REF}"
)

DEFAULT_CACHE_PATH = Path.home() / ".cache" / "pali_translator" / "lexicon.json"


def _auth_headers() -> dict[str, str]:
    """Return HTTP headers, including a GitHub token if GITHUB_TOKEN is set."""
    headers: dict[str, str] = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "pali-translator",
    }
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def _fetch_json(url: str) -> Any:
    req = urllib.request.Request(url, headers=_auth_headers())
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            raise RuntimeError(
                "GitHub API returned 403. You may be hitting the unauthenticated rate limit. "
                "Set the GITHUB_TOKEN environment variable to a personal access token to increase the limit."
            ) from exc
        raise


def _normalize(term: str) -> str:
    """Return the ASCII-lowercase normalized form used as the lexicon key."""
    normalized = unicodedata.normalize("NFKD", term)
    stripped = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    lowered = stripped.lower()
    return re.sub(r"[^a-z0-9]+", "_", lowered).strip("_")


def _fetch_lexicon_from_github() -> dict[str, dict]:
    """Download all term JSON files from shiny-adventure and return an index."""
    tree_data = _fetch_json(_GITHUB_TREE_URL)
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
            continue

        key = record.get("normalized_term") or _normalize(record.get("term", ""))
        if key:
            lexicon[key] = record
            # Also index by the display term (diacritic form) normalised
            display_key = _normalize(record.get("term", ""))
            if display_key and display_key != key:
                lexicon[display_key] = record

    return lexicon


class Lexicon:
    """In-memory Pali lexicon loaded from the shiny-adventure repository.

    On first use the data is downloaded from GitHub and cached locally so
    subsequent loads are fast and work offline.
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

        Lookup is case-insensitive and diacritic-insensitive.
        """
        return self._index.get(_normalize(term))

    def __len__(self) -> int:
        return len(self._index)

    def __contains__(self, term: str) -> bool:
        return _normalize(term) in self._index

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self, *, refresh: bool) -> None:
        if not refresh and self._cache_path.exists():
            with self._cache_path.open(encoding="utf-8") as fh:
                self._index = json.load(fh)
            return

        self._index = _fetch_lexicon_from_github()
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        with self._cache_path.open("w", encoding="utf-8") as fh:
            json.dump(self._index, fh, ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, dict]) -> "Lexicon":
        """Create a :class:`Lexicon` from a pre-built dictionary (for testing)."""
        instance = cls.__new__(cls)
        instance._cache_path = Path("/dev/null")
        instance._index = data
        return instance
