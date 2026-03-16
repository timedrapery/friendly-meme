# Development guide

## Prerequisites

- Python 3.10 or later
- Git

No third-party packages are required — the project uses only the Python
standard library.

---

## Setup

```bash
# 1. Clone the repository
git clone https://github.com/timedrapery/friendly-meme.git
cd friendly-meme

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install the package in editable mode
pip install -e .
```

Check the installed CLI:

```bash
pali-translator --help
```

---

## Running tests

The test suite is entirely offline — no network access or GitHub token needed.

```bash
python -m unittest discover -s tests -v
```

Build the distribution artifacts before release work:

```bash
python -m pip install "setuptools>=68" build
python -m build
```

All tests should pass.  Tests use a small synthetic lexicon injected via
`Lexicon.from_dict(...)` so there is no dependency on the upstream data source.

---

## Project layout

```
friendly-meme/
├── pali_translator/        # Main package
│   ├── __init__.py         # Public API surface
│   ├── __main__.py         # python -m pali_translator entry point
│   ├── cli.py              # CLI argument parsing and output
│   ├── lexicon.py          # GitHub fetch, caching, and term lookup
│   └── translator.py       # Tokenisation and translation logic
├── tests/
│   └── test_translator.py  # Full offline test suite
├── docs/                   # Additional documentation
│   ├── architecture.md     # System design and module breakdown
│   ├── development-guide.md  (this file)
│   └── usage.md            # CLI and API usage examples
├── .github/
│   ├── workflows/ci.yml    # CI: test on Python 3.10–3.13
│   ├── ISSUE_TEMPLATE/     # Bug and feature request templates
│   ├── pull_request_template.md
│   └── dependabot.yml      # Automated dependency updates
├── pyproject.toml          # Build config and package metadata
├── CHANGELOG.md
├── CONTRIBUTING.md
└── README.md
```

---

## Code standards

- **Python 3.10+**, standard library only.
- **Type annotations** on all public functions and methods.
- **Docstrings** on every module, class, and public function.
- **Tests** in `tests/` using `unittest`.  Keep the synthetic lexicon in
  `tests/support.py` small and representative.

---

## Adding or updating terms

Term data lives in the separate
[timedrapery/shiny-adventure](https://github.com/timedrapery/shiny-adventure)
repository.  To add or revise a term, contribute there.

To pull the latest data into your local cache:

```bash
pali-translator --refresh dukkha
```

---

## Releasing

1. Update `version` in `pyproject.toml`.
2. Move the relevant notes from `[Unreleased]` to a new dated release section in `CHANGELOG.md`.
3. Run the test suite and build artifacts locally.
4. Commit, tag, and push:

```bash
python -m unittest discover -s tests -v
python -m build
git tag v0.2.0
git push origin main --tags
```

5. Publish a GitHub release. The release workflow scaffold in `.github/workflows/release.yml`
  builds the package and can publish to PyPI when GitHub OIDC trusted
  publishing is configured for the repository.
