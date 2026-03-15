# Usage guide

## Installation

```bash
# From source (recommended for development)
git clone https://github.com/timedrapery/friendly-meme.git
cd friendly-meme
pip install -e .

# Direct install (once a release is published to PyPI)
# pip install pali-translator
```

---

## CLI quick reference

### Look up a single term

```bash
python -m pali_translator dukkha
```

Output:

```
Loading lexicon… (this may take a moment on first run while the cache is built)
Lexicon loaded: 312 entries

  'dukkha'  → 'dissatisfaction'
    alternatives : unsatisfactoriness, stress
    definition   :
    The unstable and unsatisfactory character of conditioned experience.
    entry type   : major
```

### Translate a passage

```bash
python -m pali_translator --translate "dukkha samudayo nirodho maggo"
```

Output:

```
Original   : dukkha samudayo nirodho maggo
Translated : dissatisfaction arising cessation path

Resolved terms:
  'dukkha'    → 'dissatisfaction'
  'samudayo'  → 'arising'
  'nirodho'   → 'cessation'
  'maggo'     → 'path'
```

### Verbose passage translation

```bash
python -m pali_translator --verbose --translate "dukkha nibbana"
```

The `--verbose` flag adds definitions and alternative translations for
each resolved term in the passage output.

### Force a fresh lexicon download

```bash
python -m pali_translator --refresh dukkha
```

This deletes the local cache and re-fetches all term files from GitHub.
Useful after upstream lexicon updates.

---

## Library API

Import the package directly for use in your own Python code:

```python
from pali_translator import Lexicon, lookup_term, translate_text

# Load lexicon (cached after first run)
lexicon = Lexicon()

# Single-term lookup
match = lookup_term("dukkha", lexicon)
if match:
    print(match.preferred_translation)   # "dissatisfaction"
    print(match.alternative_translations) # ["unsatisfactoriness", "stress"]
    print(match.definition)

# Passage translation
result = translate_text("dukkha samudayo nirodho maggo", lexicon)
print(result.translated)       # "dissatisfaction arising cessation path"
print(result.unknown_tokens)   # terms not found in the lexicon
```

### `Lexicon`

| Parameter    | Type              | Default                                   | Description                          |
|--------------|-------------------|-------------------------------------------|--------------------------------------|
| `cache_path` | `Path \| None`    | `~/.cache/pali_translator/lexicon.json`   | Override the cache file location     |
| `refresh`    | `bool`            | `False`                                   | Force re-download from GitHub        |

Methods: `lookup(term)`, `__len__()`, `__contains__(term)`,
`Lexicon.from_dict(data)` (for testing).

### `TermMatch`

Dataclass returned by `lookup_term`:

| Field                     | Type        | Description                                         |
|---------------------------|-------------|-----------------------------------------------------|
| `token`                   | `str`       | Original input word                                 |
| `preferred_translation`   | `str`       | OSF-preferred English rendering                     |
| `alternative_translations`| `list[str]` | Accepted alternatives                               |
| `definition`              | `str`       | Short explanatory definition                        |
| `entry_type`              | `str`       | `"major"` or `"minor"`                              |
| `untranslated_preferred`  | `bool`      | `True` if the term is intentionally kept in Pāli    |

### `TranslationResult`

Dataclass returned by `translate_text`:

| Field            | Type              | Description                                   |
|------------------|-------------------|-----------------------------------------------|
| `original`       | `str`             | Unchanged input text                          |
| `translated`     | `str`             | Text with known terms replaced                |
| `matches`        | `list[TermMatch]` | All resolved term matches (including kept-Pāli) |
| `unknown_tokens` | `list[str]`       | Tokens not found in the lexicon               |

---

## Authentication

By default, the lexicon fetcher makes unauthenticated GitHub API requests
(60 requests/hour limit).  On initial cache build, several hundred files
are downloaded from `raw.githubusercontent.com` — those downloads do **not**
count against the API rate limit.

If you hit rate limits:

```bash
export GITHUB_TOKEN=ghp_your_token_here
python -m pali_translator --refresh dukkha
```

The token is only used for the single git-tree API call.

---

## Cache location

The assembled lexicon is cached as JSON at:

```
~/.cache/pali_translator/lexicon.json
```

Override by passing `cache_path` to `Lexicon(...)`:

```python
lexicon = Lexicon(cache_path="/tmp/my_lexicon.json")
```
