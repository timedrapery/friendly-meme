# Changelog

All notable changes to **pali-translator** are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added

- `pali_translator` Python package with three modules:
  - `lexicon.py` — fetches and caches the full OSF term database from the
    [shiny-adventure](https://github.com/timedrapery/shiny-adventure)
    repository; supports offline use via a local JSON cache.
  - `translator.py` — `lookup_term()` and `translate_text()` functions;
    honours `untranslated_preferred` policy; returns typed dataclasses.
  - `cli.py` — command-line interface (`python -m pali_translator`) with
    single-term lookup, passage translation, verbose output, and cache
    refresh modes.
- `pyproject.toml` for standard installable packaging (`pip install .`
  registers a `pali-translator` console script).
- 22 offline unit tests covering normalisation, diacritic stripping,
  case-insensitive lookup, translation policy, punctuation handling, and
  unknown-token reporting.
- `CONTRIBUTING.md` with setup, testing, and contribution guidelines.
- `CHANGELOG.md` (this file).
