# Usage guide

## Desktop GUI

The Tkinter workbench is the primary interface for non-technical users.

### Launching

```bash
# Console script (after pip install -e .)
pali-translator-gui

# Module entry point
python -m pali_translator.gui
```

### First run

On first launch the app downloads and caches the full shiny-adventure lexicon.
The status bar shows progress.  Subsequent launches load from the local cache
and start immediately.  If you are offline and the cache exists, the app works
without any network access.

### Translate a passage

1. Type or paste a Pāli passage into the **Source (Pāli)** box on the left.
2. Click **Translate** (or press Ctrl+Return).
3. The translated passage appears in the **Translation** panel on the right.
4. The **Token Analysis** table shows every token with:
   - original token and normalised form
   - `matched` / `UNKNOWN` status (colour-coded)
   - preferred translation per OSF policy
   - entry type (`major` / `minor`)
   - whether the term is kept in Pāli by policy
   - definition excerpt and alternatives

Unknown tokens appear in red. They are passed through unchanged in the
translation output.

### Inspect a term

- Click any row in the Token Analysis table.  The **Term Inspector** panel
  updates immediately with the full lexicon record.
- Alternatively, type a term into the **Term Lookup** field and click
  **Lookup** (or press Return).

### Copy and export

- **Copy Output** button (or Edit > Copy Output / Ctrl+Shift+C) copies the
  translated passage to the clipboard.
- **File > Export as Plain Text…** saves a full session report (source,
  translation, token table, unknowns, lexicon metadata) as `.txt`.
- **File > Export as JSON…** saves a machine-readable record with all match
  data as `.json`.

### Cache and lexicon management

- **Refresh Lexicon** button re-downloads the lexicon from GitHub and updates
  the cache.  Use this when a new shiny-adventure release is available.
- **Help > Lexicon & Cache Info** shows the current cache path, entry count,
  and whether the lexicon was loaded from cache or the network.

---

## Installation

```bash
# From source (recommended for development)
git clone https://github.com/timedrapery/friendly-meme.git
cd friendly-meme
pip install -e .

# Direct install (once a release is published to PyPI)
# pip install pali-translator
```

The editable install registers two console commands:

- `pali-translator` — the CLI
- `pali-translator-gui` — the desktop GUI workbench

You can also use `python -m pali_translator ...` and
`python -m pali_translator.gui` as alternative entry points.

---

## CLI quick reference

### Look up a single term

```bash
pali-translator dukkha
```

Output:

```
Loading lexicon... (first run may take a moment while the cache is built)
Loaded lexicon: 312 entries (cache).

  'dukkha'  → 'dissatisfaction'
    alternatives : unsatisfactoriness, stress
    definition   :
    The unstable and unsatisfactory character of conditioned experience.
    entry type   : major
```

### Translate a passage

```bash
pali-translator --translate "dukkha samudayo nirodho maggo"
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
pali-translator --verbose --translate "dukkha nibbana"
```

The `--verbose` flag adds definitions and alternative translations for
each resolved term in the passage output.

### JSON output for scripting

```bash
pali-translator --json --translate "dukkha nibbana"
```

Output:

```json
{
  "mode": "translate",
  "original": "dukkha nibbana",
  "translated": "dissatisfaction unbinding",
  "matches": [
    {
      "token": "dukkha",
      "preferred_translation": "dissatisfaction",
      "alternative_translations": [
        "unsatisfactoriness",
        "stress"
      ],
      "definition": "The unstable and unsatisfactory character of conditioned experience.",
      "entry_type": "major",
      "untranslated_preferred": false
    }
  ],
  "unknown_tokens": []
}
```

### Force a fresh lexicon download

```bash
pali-translator --refresh dukkha
```

This ignores the local cache for the current run and rebuilds it from GitHub.
Useful after upstream lexicon updates.

### Use a project-local cache

```bash
pali-translator --cache-path .cache/pali-lexicon.json dukkha
```

This is useful in reproducible local workflows where you want the cache to live
inside a project directory rather than under the user-level default cache path.

### Inspect lexicon/cache status

```bash
pali-translator --info
```

Output:

```
Lexicon status:
  entries          : 312
  cache path       : /home/user/.cache/pali_translator/lexicon.json
  loaded from cache: True
  cache exists     : True
```

For machine-readable status:

```bash
pali-translator --info --json
```

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
print(lexicon.info())          # cache path and load metadata
```

### `Lexicon`

| Parameter    | Type              | Default                                   | Description                          |
|--------------|-------------------|-------------------------------------------|--------------------------------------|
| `cache_path` | `Path \| None`    | `~/.cache/pali_translator/lexicon.json`   | Override the cache file location     |
| `refresh`    | `bool`            | `False`                                   | Force re-download from GitHub        |

Methods: `lookup(term)`, `__len__()`, `__contains__(term)`,
`info()`, `Lexicon.from_dict(data)` (for testing).

Properties: `cache_path`, `loaded_from_cache`, `cache_warning`.

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
pali-translator --refresh dukkha
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

If the cache file is corrupt or empty, `Lexicon(...)` raises `RuntimeError`
instead of silently proceeding with a broken index. Re-run with `refresh=True`
or delete the cache file to rebuild it.

## Fallback behavior

- Unknown terms remain unchanged in the translated output.
- Unknown terms are listed in `unknown_tokens` and in the CLI summary.
- Punctuation-only tokens are preserved as-is and are not reported as unknown.
- Terms marked `untranslated_preferred` remain in Pāli and still appear in
  `matches`, so callers can tell that the token was recognized intentionally.
