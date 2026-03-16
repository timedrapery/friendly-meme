# pali-translator

[![CI](https://github.com/timedrapery/friendly-meme/actions/workflows/ci.yml/badge.svg)](https://github.com/timedrapery/friendly-meme/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A lexicon-governed Pāli translator: **desktop GUI workbench**, command-line
tool, and Python library — built around the
[shiny-adventure](https://github.com/timedrapery/shiny-adventure) term policy.

---

## Overview

`pali-translator` is not a generic machine translation system. It consumes
structured lexical policy from
[timedrapery/shiny-adventure](https://github.com/timedrapery/shiny-adventure),
applies those rules deterministically, and exposes the result through:

- a **desktop GUI workbench** for non-technical users and editorial review
- a **command-line interface** for scripting and automation
- a **Python library** for programmatic integration

It is designed for local, inspectable workflows:

- explicit lexicon loading
- predictable cache behaviour
- readable structured results
- token-by-token editorial transparency
- no runtime dependencies beyond the Python standard library

---

## What it does

`pali-translator` looks up each Pāli term in the upstream lexicon and applies
the preferred contemporary-English rendering attached to that term. Terms marked
as `untranslated_preferred` remain in Pāli by policy, and unknown tokens remain
visible in the output rather than being guessed.

The desktop GUI makes these same mechanics accessible to non-technical users,
with a token-by-token analysis table, term inspector, and one-click export.

---

## Desktop GUI

The Tkinter workbench provides:

- **Source input** — enter any Pāli passage
- **Translate button** — translates the passage token by token
- **Token analysis table** — every token with its match status, preferred
  translation, entry type, policy flag, definition, and alternatives
- **Term inspector** — click any table row (or search directly) to view a
  term's full lexicon record including definition and OSF policy notes
- **Translation output** — rendered passage with copy-to-clipboard
- **Export** — plain-text or JSON session reports including metadata
- **Refresh lexicon** — force a fresh download from GitHub
- **Status bar** — shows lexicon source (cache / network), entry count, and
  per-action feedback
- **About / Lexicon & Cache Info** — shows the cache path and load details

#### Launch the GUI

```bash
# After pip install -e .
pali-translator-gui

# Without installing (module entry point)
python -m pali_translator.gui
```

> **Tkinter note:** Tkinter comes bundled with the standard CPython installers
> for Windows and macOS. On headless Linux servers it may need to be installed
> separately (`sudo apt-get install python3-tk`). The CLI and library work fine
> without a display.

---

## Features

- **Desktop GUI** — Tkinter workbench for non-technical users and editorial
  review sessions
- **Single-term lookup** — retrieve the preferred translation, alternatives,
  definition, and entry type for any Pāli word
- **Passage translation** — tokenise and translate a full Pāli passage in one
  call, with per-token match metadata
- **Policy-aware** — terms marked `untranslated_preferred` in the lexicon are
  intentionally kept in Pāli
- **Offline cache** — lexicon data is fetched from GitHub once and cached at
  `~/.cache/pali_translator/lexicon.json`; subsequent runs work without
  network access
- **Export** — plain-text and JSON session reports with full token analysis
- **Scriptable CLI** — optional JSON output and predictable exit codes for
  shell automation
- **Explicit cache control** — override cache location with `--cache-path` or
  `Lexicon(cache_path=...)`
- **Inspectable status** — inspect lexicon and cache state with
  `pali-translator --info`
- **Typed API** — all public functions return dataclasses (`TermMatch`,
  `TranslationResult`) rather than plain strings
- **Zero runtime dependencies** — Python 3.10+ standard library only

---

## Repository structure

```
pali_translator/        Main package
├── lexicon.py          GitHub fetch, caching, and term lookup
├── translator.py       Tokenisation and translation logic
├── cli.py              Command-line interface
└── gui/                Desktop GUI workbench (Tkinter)
    ├── app.py          Main window and event wiring
    ├── controller.py   Application state (no Tk deps)
    ├── widgets.py      Reusable Tk widget components
    ├── export.py       Plain-text and JSON report generation
    └── __main__.py     python -m pali_translator.gui entry point

tests/                  Offline unit tests (no network, no display needed)
docs/                   Extended documentation
    ├── architecture.md   System design and module breakdown
    ├── usage.md          Full CLI and library API reference
    └── development-guide.md  Contributor setup and workflow
```

---

## Installation

```bash
git clone https://github.com/timedrapery/friendly-meme.git
cd friendly-meme
pip install -e .
```

This installs two commands:

- `pali-translator` — the command-line interface
- `pali-translator-gui` — the desktop GUI workbench

`python -m pali_translator ...` and `python -m pali_translator.gui` remain
available as alternative entry points.

---

## Quickstart

### Desktop GUI

```bash
pali-translator-gui
# or: python -m pali_translator.gui
```

On first launch the lexicon is automatically downloaded and cached. Subsequent
launches load from the cache and start in under a second.
Offline use works as long as the cache exists.

### CLI

```bash
# Look up a single Pāli term
pali-translator dukkha

# Translate a multi-word passage
pali-translator --translate "dukkha samudayo nirodho maggo"

# Verbose output — definitions and alternatives
pali-translator --verbose --translate "dukkha nibbana"

# Force a fresh download of the lexicon cache
pali-translator --refresh dukkha

# Emit machine-readable output
pali-translator --json --translate "dukkha nibbana"

# Keep the cache in a project-local location
pali-translator --cache-path .cache/pali-lexicon.json dukkha

# Inspect lexicon/cache status without translating
pali-translator --info
```

The CLI writes progress and load diagnostics to stderr. Human-readable results
or JSON payloads are written to stdout.

Exit codes:

- `0` success
- `1` single-term lookup did not find a match
- `2` lexicon loading failed

### Library API

```python
from pali_translator import Lexicon, __version__, lookup_term, translate_text

lexicon = Lexicon()                           # fetches and caches on first run
result  = translate_text("dukkha nibbana", lexicon)
print(result.translated)                      # "dissatisfaction unbinding"
print(result.unknown_tokens)                  # tokens not found in the lexicon
print(__version__)                            # installed package version
```

`Lexicon.info()` returns lightweight metadata about the loaded lexicon,
including the cache path and whether the index came from disk or a fresh
download.

## Cache and data source

The lexicon comes from
[timedrapery/shiny-adventure](https://github.com/timedrapery/shiny-adventure).
On first load, `pali-translator` downloads the term records, assembles a local
index, and stores it at `~/.cache/pali_translator/lexicon.json` unless another
path is provided.

Unknown terms are not guessed. They are left in place and surfaced in
`TranslationResult.unknown_tokens` or in the CLI output so they can be handled
explicitly.

If the cache is corrupt or empty, the tool reports that directly and asks for a
refresh instead of silently continuing with a broken index.

## Relationship to shiny-adventure

`pali-translator` is an application layer over the upstream lexicon. Term data,
translation policy, and editorial decisions belong in
[timedrapery/shiny-adventure](https://github.com/timedrapery/shiny-adventure).
This repository is responsible for loading that policy, applying it
predictably, and exposing it cleanly through Python and CLI interfaces.

## Project boundaries

This repository does not aim to be:

- a generic AI translator
- a broad NLP research project
- a substitute for editorial review
- a source of independent term policy outside the upstream lexicon

See [`docs/usage.md`](docs/usage.md) for the full API reference.

---

## Development

```bash
# Run the test suite (offline — no network or token required)
python -m unittest discover -s tests -v
```

```bash
# Build a source distribution and wheel
python -m pip install "setuptools>=68" build
python -m build
```

See [`docs/development-guide.md`](docs/development-guide.md) for the full
contributor workflow, including setup, code standards, and release steps.

---

## Contributing

Contributions are welcome.  Please read [`CONTRIBUTING.md`](CONTRIBUTING.md)
and open an issue before starting significant work.

Term data lives in the separate
[timedrapery/shiny-adventure](https://github.com/timedrapery/shiny-adventure)
repository.  To add or revise a term, contribute there.

---

## License

[MIT](LICENSE)