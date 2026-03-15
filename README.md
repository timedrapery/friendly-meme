# friendly-meme

A Pāli-to-contemporary-English translator powered by the
[shiny-adventure](https://github.com/timedrapery/shiny-adventure) lexicon.

The translator looks up each Pāli term in the Open Sangha Foundation (OSF)
lexicon and substitutes the project's preferred contemporary English rendering,
respecting the documented translation policy for each term.

---

## Quick start

```bash
# look up a single Pāli term
python -m pali_translator dukkha

# translate a multi-word Pāli passage
python -m pali_translator --translate "dukkha samudayo nirodho maggo"

# verbose output includes definitions and alternative translations
python -m pali_translator --verbose dukkha

# force a fresh download of the lexicon cache
python -m pali_translator --refresh dukkha
```

The lexicon data is fetched from GitHub on first run and cached at
`~/.cache/pali_translator/lexicon.json`. Subsequent runs load from the
local cache and work offline.

---

## How it works

1. **Lexicon** (`pali_translator/lexicon.py`) — downloads all `terms/major/`
   and `terms/minor/` JSON files from the shiny-adventure repository and
   builds an in-memory lookup index keyed by the ASCII-normalised term.

2. **Translator** (`pali_translator/translator.py`) — tokenises a Pāli
   passage, looks up each token, and substitutes the `preferred_translation`
   field value. Terms marked `untranslated_preferred: true` are left in
   Pāli as per the lexicon policy.

3. **CLI** (`pali_translator/cli.py`) — thin command-line wrapper around the
   translator, supporting single-term lookup and full-passage translation.

---

## Running tests

```bash
python -m unittest discover -s tests
```

No external dependencies are required; all tests use a small synthetic
lexicon and run entirely offline.

---

## Data source

Term data is drawn from the
[timedrapery/shiny-adventure](https://github.com/timedrapery/shiny-adventure)
repository, which is a structured Pāli-to-English translation lexicon
maintained by the Open Sangha Foundation.