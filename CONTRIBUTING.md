# Contributing

Thank you for your interest in **pali-translator**.

---

## Development setup

```bash
# 1. Fork and clone the repository
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
python -m unittest discover -s tests -v
```

Builds should also succeed before release-oriented changes:

```bash
python -m pip install "setuptools>=68" build
python -m build
```

---

## Submitting changes

1. **Open an issue first** for anything beyond a trivial fix, so the approach
   can be discussed before you invest time writing code.
2. **Fork** the repository and create a branch from `main`:
   ```bash
   git checkout -b fix/describe-the-fix
   # or
   git checkout -b feat/describe-the-feature
   ```
3. **Make your changes**, keeping commits focused and the test suite green.
4. **Update `CHANGELOG.md`** — add a line under `[Unreleased]` describing
   what you changed.
5. **Open a pull request** against `main`.  The pull request template will
   prompt you for the relevant details.

### Commit style

Use short, imperative subject lines (50 chars or fewer):

```
fix: strip trailing punctuation before lexicon lookup
feat: add --output-json flag to CLI
docs: clarify cache refresh behaviour
```

---

## Code style

- Python 3.10+, standard library only (no runtime dependencies).
- Type annotations on all public functions and methods.
- Docstrings on every module, class, and public function.
- Tests live in `tests/` and use `unittest`.

---

## Refreshing the lexicon cache

The first time you run the translator it downloads all term files from the
[shiny-adventure](https://github.com/timedrapery/shiny-adventure) repository
and caches them at `~/.cache/pali_translator/lexicon.json`.

To force a fresh download:

```bash
pali-translator --refresh dukkha
```

If you hit the GitHub unauthenticated rate limit (60 requests/hour), set a
personal access token:

```bash
export GITHUB_TOKEN=ghp_...
pali-translator --refresh dukkha
```

---

## Lexicon data

Term data lives in the separate
[timedrapery/shiny-adventure](https://github.com/timedrapery/shiny-adventure)
repository.  To add or revise a term, contribute there rather than here.
