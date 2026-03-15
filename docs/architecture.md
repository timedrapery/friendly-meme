# Architecture

## Overview

`pali-translator` is a pure-Python library and CLI tool.  It has no
third-party runtime dependencies — everything is built on the Python
standard library.

```
pali_translator/
├── __init__.py      # Public API exports
├── __main__.py      # python -m pali_translator entry point
├── cli.py           # Argument parsing and formatted output
├── lexicon.py       # Data fetching, caching, and lookup
└── translator.py    # Tokenisation and translation logic
```

---

## Data flow

```
GitHub (shiny-adventure repo)
        │
        │  first run / --refresh
        ▼
  lexicon.py  ──────────────────────►  ~/.cache/pali_translator/lexicon.json
  _fetch_lexicon_from_github()              (subsequent runs read from here)
        │
        ▼
  Lexicon (in-memory dict)
  lookup(term) → record | None
        │
        ▼
  translator.py
  lookup_term(term, lexicon)  →  TermMatch | None
  translate_text(text, lexicon)  →  TranslationResult
        │
        ▼
  cli.py  →  formatted stdout output
```

---

## Key modules

### `lexicon.py`

Responsible for all data access:

1. **Fetch** — calls the GitHub git-tree API once to get the full file list
   for `timedrapery/shiny-adventure`, then downloads each
   `terms/**/*.json` file from `raw.githubusercontent.com`.
2. **Normalise** — strips diacritics, lowercases, and collapses non-ASCII
   characters to underscores so that `nibbāna` and `nibbana` resolve to
   the same key.
3. **Cache** — writes the assembled index to
   `~/.cache/pali_translator/lexicon.json` so subsequent runs are
   instant and offline-capable.
4. **Expose** — the `Lexicon` class provides `lookup(term)`,
   `__len__`, `__contains__`, and a `from_dict` class method for
   dependency injection in tests.

### `translator.py`

Pure translation logic with no I/O:

- `lookup_term(term, lexicon)` → `TermMatch | None`
- `translate_text(text, lexicon)` → `TranslationResult`

Both return typed dataclasses so callers get structured data rather
than plain strings.  Translation policy (`untranslated_preferred`) is
respected: terms the OSF lexicon marks as "leave in Pāli" are passed
through unchanged but still appear in `TranslationResult.matches`.

### `cli.py`

Thin wrapper around the library functions.  Handles argument parsing
(`argparse`), lexicon loading progress messages, and human-readable
output formatting.  Returns integer exit codes for shell scripting.

---

## Normalisation algorithm

Used in both `lexicon.py` and `translator.py` (duplicated intentionally
to keep each module independently importable):

1. NFKD-decompose the string.
2. Drop all Unicode combining marks (diacritics).
3. Lowercase the result.
4. Replace any run of non-alphanumeric ASCII characters with `_`.
5. Strip leading/trailing underscores.

This means `Nibbāna`, `nibbana`, and `nibbāna` all resolve to `nibbana`.

---

## Cache format

The cache is a flat JSON object mapping normalised key → raw record dict:

```json
{
  "dukkha": {
    "term": "dukkha",
    "normalized_term": "dukkha",
    "entry_type": "major",
    "preferred_translation": "dissatisfaction",
    ...
  },
  "nibbana": { ... }
}
```

Records are indexed by both `normalized_term` (the field value from the
source JSON) and the normalised form of the display `term` field, so
diacritic variants resolve to the same record.

---

## Testing approach

All tests live in `tests/test_translator.py` and use `unittest`.
A small synthetic lexicon (`Lexicon.from_dict(...)`) replaces network
access entirely, so the suite runs offline with no credentials needed.

See [development-guide.md](development-guide.md) for how to run the
tests.
