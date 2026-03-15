# Contributing

Thank you for your interest in **pali-translator**.

---

## Development setup

```bash
# 1. Clone the repository
git clone https://github.com/timedrapery/friendly-meme.git
cd friendly-meme

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install the package in editable mode (no extra deps required)
pip install -e .
```

---

## Running tests

All tests are offline — no GitHub token or network access needed.

```bash
python -m unittest discover -s tests
```

---

## Refreshing the lexicon cache

The first time you run the translator it downloads all term files from the
[shiny-adventure](https://github.com/timedrapery/shiny-adventure) repository
and caches them at `~/.cache/pali_translator/lexicon.json`.

To force a fresh download:

```bash
python -m pali_translator --refresh dukkha
```

If you hit the GitHub unauthenticated rate limit (60 requests/hour), set a
personal access token:

```bash
export GITHUB_TOKEN=ghp_...
python -m pali_translator --refresh dukkha
```

---

## Code style

- Python 3.10+, standard library only (no runtime dependencies).
- Type annotations on all public functions and methods.
- Docstrings on every module, class, and public function.
- Tests live in `tests/` and use `unittest`.

---

## Lexicon data

Term data lives in the separate
[timedrapery/shiny-adventure](https://github.com/timedrapery/shiny-adventure)
repository. To add or revise a term, contribute there rather than here.
