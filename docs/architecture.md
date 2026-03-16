# Architecture

## Overview

`pali-translator` is a pure-Python Pāli translation tool with three
presentation surfaces and no third-party runtime dependencies.

```
pali_translator/
├── __init__.py      # Public API exports
├── __main__.py      # python -m pali_translator entry point (CLI)
├── cli.py           # Argument parsing and formatted output
├── lexicon.py       # Data fetching, caching, and lookup
├── translator.py    # Tokenisation and translation logic
├── phrases.py       # Multi-word phrase index and greedy scan
└── gui/             # Desktop GUI layer (Tkinter)
    ├── __init__.py
    ├── __main__.py  # python -m pali_translator.gui entry point
    ├── app.py       # Tk root window, event wiring, layout
    ├── controller.py# Application state — no Tk imports
    ├── widgets.py   # Reusable Tk widget components
    ├── export.py    # Plain-text, JSON, and Markdown report generation
    ├── history.py   # In-session translation history log
    ├── concordance.py# Token concordance builder
    ├── filter.py    # Token row filtering utilities
    ├── settings.py  # Persistent user settings (JSON)
    ├── interlinear.py# Interlinear gloss row builder
    ├── notes.py     # Session / token / phrase annotation store
    └── compare.py   # Session diff and ComparisonSummary
```

---

## Architectural boundary: core vs. GUI

The critical design rule is that `gui/controller.py` and `gui/export.py`
have **no tkinter imports**.  They can be imported and tested in any headless
environment.

```
pali_translator/             ← core layer (no Tk)
├── lexicon.py
├── translator.py
└── gui/
    ├── controller.py        ← application state only, no Tk
    ├── export.py            ← serialisation only, no Tk
    ├── app.py               ← Tk wiring — imports from controller
    └── widgets.py           ← Tk components only
```

`app.py` is the only module that touches `tkinter`.  It:

1. Instantiates a `Controller` and calls it from background threads for
   blocking operations (lexicon load).
2. Calls `root.after()` to post results back to the Tk main thread.
3. Delegates all business logic to `Controller`; it never touches the
   lexicon or translator directly.

---

## Data flow

```
GitHub (shiny-adventure repo)
        │
        │  first run / --refresh / Refresh Lexicon button
        ▼
  lexicon.py  ──────────────────────►  ~/.cache/pali_translator/lexicon.json
  _fetch_lexicon_from_github()              (subsequent runs read from here)
        │
        ▼
  Lexicon (in-memory dict)
  lookup(term) → record | None
        │
        ├─► translator.py  ──────────────────────────────────► CLI stdout
        │   lookup_term(term, lexicon)  → TermMatch | None
        │   translate_text(text, lexicon) → TranslationResult
        │
        └─► gui/controller.py  ──────────────────────────────► Tk widgets
            translate(text) → TranslationResult
            lookup(term)    → TermMatch | None
            current_session → TranslationSession
                                    │
                                    └─► gui/export.py ──────► file on disk
                                        export_json(session)
                                        export_plain_text(session)
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
      Invalid or empty caches are rejected explicitly rather than being used
      silently.
4. **Expose** — the `Lexicon` class provides `lookup(term)`,
      `__len__`, `__contains__`, `info()`, cache metadata properties, and a
      `from_dict` class method for dependency injection in tests.

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
(`argparse`), lexicon loading progress messages on stderr, human-readable
output formatting, and JSON payload output for scripting. Returns integer exit
codes for shell scripting.

### `gui/controller.py`

Application state manager — the only point of contact between the GUI and
the translation engine.  No tkinter imports.

Key responsibilities:
- Wraps `Lexicon` construction (blocking call → put on background thread)
- Wraps `translate_text` and `lookup_term`
- Builds `TokenRow` objects for each token (richer than `TermMatch` for table display)
- Records a `TranslationSession` after each translation for export

### `gui/app.py`

Main `tk.Tk` subclass.  Builds the window, wires events to
`Controller` calls, and reflects results back into widgets.  Manages
background threads for lexicon loading using `root.after()` callbacks.

### `gui/widgets.py`

Self-contained Tk widget components:

- `TokenTable` — `ttk.Treeview` with typed columns for per-token analysis
- `TermInspectorFrame` — styled `tk.Text` panel for a single term's record
- `StatusBar` — bottom-of-window single-line status display

### `gui/export.py`

Serialisation only — no Tk.

- `export_json(session)` → str
- `export_plain_text(session)` → str

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
      cli.py  →  stdout payloads + stderr progress/errors
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
      Invalid or empty caches are rejected explicitly rather than being used
      silently.
4. **Expose** — the `Lexicon` class provides `lookup(term)`,
      `__len__`, `__contains__`, `info()`, cache metadata properties, and a
      `from_dict` class method for
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
(`argparse`), lexicon loading progress messages on stderr, human-readable
output formatting, and JSON payload output for scripting. Returns integer exit
codes for shell scripting.

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

When a cache write fails after a successful download, the lexicon still remains
usable for the current process and the instance records a cache warning for the
caller to surface.

---

## Testing approach

Tests use `unittest` and are split by concern:

- `tests/test_translator.py` for lookup and translation semantics
- `tests/test_lexicon.py` for cache handling and fetch failures
- `tests/test_cli.py` for CLI smoke coverage and JSON output

A small synthetic lexicon replaces network access in the main suite, while
cache/fetch tests use mocks and temporary directories to keep behavior explicit
and offline-friendly.

See [development-guide.md](development-guide.md) for how to run the
tests.
