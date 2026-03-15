# pali-translator

[![CI](https://github.com/timedrapery/friendly-meme/actions/workflows/ci.yml/badge.svg)](https://github.com/timedrapery/friendly-meme/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A Pāli-to-contemporary-English translator powered by the
[shiny-adventure](https://github.com/timedrapery/shiny-adventure) lexicon.

---

## Overview

`pali-translator` looks up each Pāli term in the Open Sangha Foundation (OSF)
lexicon and substitutes the project's preferred contemporary English rendering,
respecting the documented translation policy for each term.

It works as both a **command-line tool** and an **importable Python library**.
No third-party packages are required — the project uses only the Python
standard library.

---

## Why this project exists

Translating Pāli texts requires consistent, policy-governed word choices.
The OSF lexicon (`shiny-adventure`) defines preferred and discouraged
renderings for hundreds of terms, but applying those choices mechanically
across a passage is tedious.  `pali-translator` automates that substitution
while surfacing the editorial decisions behind each choice.

---

## Features

- **Single-term lookup** — retrieve the preferred translation, alternatives,
  definition, and entry type for any Pāli word
- **Passage translation** — tokenise and translate a full Pāli passage in one
  call, with per-token match metadata
- **Policy-aware** — terms marked `untranslated_preferred` in the lexicon are
  intentionally kept in Pāli
- **Offline cache** — lexicon data is fetched from GitHub once and cached at
  `~/.cache/pali_translator/lexicon.json`; subsequent runs work without
  network access
- **Typed API** — all public functions return dataclasses (`TermMatch`,
  `TranslationResult`) rather than plain strings
- **Zero runtime dependencies** — Python 3.10+ standard library only

---

## Repository structure

```
pali_translator/        Main package
├── lexicon.py          GitHub fetch, caching, and term lookup
├── translator.py       Tokenisation and translation logic
└── cli.py              Command-line interface

tests/                  Offline unit tests (synthetic lexicon, no network)
docs/                   Extended documentation
  ├── architecture.md   System design and module breakdown
  ├── usage.md          Full CLI and library API reference
  └── development-guide.md  Contributor setup and workflow
```

---

## Getting started

```bash
git clone https://github.com/timedrapery/friendly-meme.git
cd friendly-meme
pip install -e .
```

No additional packages needed.

---

## Usage

```bash
# Look up a single Pāli term
python -m pali_translator dukkha

# Translate a multi-word passage
python -m pali_translator --translate "dukkha samudayo nirodho maggo"

# Verbose output — definitions and alternatives
python -m pali_translator --verbose --translate "dukkha nibbana"

# Force a fresh download of the lexicon cache
python -m pali_translator --refresh dukkha
```

### Library API

```python
from pali_translator import Lexicon, lookup_term, translate_text

lexicon = Lexicon()                           # fetches and caches on first run
result  = translate_text("dukkha nibbana", lexicon)
print(result.translated)                      # "dissatisfaction unbinding"
print(result.unknown_tokens)                  # tokens not found in the lexicon
```

See [`docs/usage.md`](docs/usage.md) for the full API reference.

---

## Development

```bash
# Run the test suite (offline — no network or token required)
python -m unittest discover -s tests -v
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

## Data source

Term data is drawn from
[timedrapery/shiny-adventure](https://github.com/timedrapery/shiny-adventure),
a structured Pāli-to-English translation lexicon maintained by the Open Sangha
Foundation.

---

## License

[MIT](LICENSE)