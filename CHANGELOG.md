# Changelog

All notable changes to **pali-translator** are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added — Desktop GUI workbench (`pali_translator/gui/`)

- `pali_translator.gui.app` — main Tkinter window with a translator workbench
  layout: resizable left/right panes, source input, translation output,
  token analysis table, term inspector, status bar, and menu bar.
- `pali_translator.gui.controller` — headless application controller with no
  Tk imports; wraps lexicon loading (designed for background threads),
  translation, single-term lookup, and session tracking.  Produces
  `TokenRow` objects for every source token, including unmatched ones.
- `pali_translator.gui.widgets` — reusable Tk widget components: `TokenTable`
  (ttk.Treeview with 8 columns and colour-tagged rows), `TermInspectorFrame`
  (styled text panel for term detail), and `StatusBar`.
- `pali_translator.gui.export` — `export_json` and `export_plain_text`
  serialise a `TranslationSession` to file; no Tk dependency.
- `pali_translator.gui.__main__` — `python -m pali_translator.gui` entry point
  with a clear error message when Tkinter is not available.
- `pali-translator-gui` console script entry in `pyproject.toml`.

### Added — Export / reporting

- `TranslationSession` dataclass captures source text, `TranslationResult`,
  per-token `TokenRow` list, `LexiconStatus`, and ISO timestamp.
- Plain-text export: source, translation, token analysis, unknown tokens,
  lexicon source and cache path.
- JSON export: full structured record including all match metadata and counts.

### Added — Tests

- `tests/test_gui_controller.py` — 25 tests for controller init, translate,
  token row fields, and lookup; no Tk or network required.
- `tests/test_export.py` — 30 tests covering JSON and plain-text export
  structure, Unicode round-tripping, and edge cases.

### Changed

- `pyproject.toml` version bumped to `0.2.0`.
- README expanded: desktop GUI overview, launch instructions, Tkinter platform
  note, updated features list and repo structure diagram.
- `docs/architecture.md` rewritten to document the GUI layer, the
  core-vs-GUI boundary, and the updated data flow.

---

## [0.1.x] — 2026-03-16 (pre-GUI sprint)

### Added

- `pali-translator --json` for machine-readable single-term and passage output.
- `pali-translator --info` for explicit lexicon/cache status inspection, with
  optional JSON output.
- `pali-translator --cache-path PATH` and `Lexicon(cache_path=...)` examples for
  explicit local cache placement.
- `Lexicon.info()`, `Lexicon.cache_path`, `Lexicon.loaded_from_cache`, and
  `Lexicon.cache_warning` for lightweight load-state inspection.
- CLI smoke tests and cache/error-path tests split into focused test modules.
- Release workflow scaffolding for build artifacts and PyPI publication via
  trusted publishing.

### Changed

- Tightened package metadata and exposed `pali_translator.__version__`.
- Reworked CLI help text and examples around the installed `pali-translator`
  command.
- CLI progress and load diagnostics now go to stderr; result payloads remain on
  stdout.
- README and docs now state project boundaries, cache semantics, and fallback
  behavior more explicitly.

### Fixed

- Broken or empty lexicon caches now fail explicitly instead of being used
  silently.
- Empty upstream lexicon downloads now raise a clear runtime error.
- Cache write failures no longer discard an otherwise usable in-memory lexicon.

---

## [0.1.x] — 2026-03-16 (pre-GUI sprint)

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
- 23 offline unit tests covering normalisation, diacritic stripping,
  case-insensitive lookup, translation policy, punctuation handling,
  unknown-token reporting, and cross-module normalisation consistency.
- `CONTRIBUTING.md`, `CHANGELOG.md`, `LICENSE` (MIT), `SECURITY.md`,
  and `CODE_OF_CONDUCT.md`.
- `docs/` directory with architecture, usage, and development-guide pages.
- GitHub Actions CI workflow testing Python 3.10, 3.11, 3.12, and 3.13.
- Issue templates, pull request template, and Dependabot configuration.

---

[Unreleased]: https://github.com/timedrapery/friendly-meme/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/timedrapery/friendly-meme/releases/tag/v0.1.0
