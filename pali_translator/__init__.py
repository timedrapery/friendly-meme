"""pali_translator — Pāli-to-contemporary-English translator.

This package exposes three public objects:

Lexicon
    Loads the full OSF term database from the ``timedrapery/shiny-adventure``
    GitHub repository, caches it locally, and provides O(1) term lookup.

lookup_term(term, lexicon) -> TermMatch | None
    Look up a single Pāli word and return its preferred English rendering plus
    metadata (alternatives, definition, entry type, translation policy flags).

translate_text(text, lexicon) -> TranslationResult
    Tokenise a Pāli passage and replace every known term with its preferred
    contemporary English rendering, leaving unknown tokens untouched and
    honouring ``untranslated_preferred`` policy entries.

Typical usage::

    from pali_translator import Lexicon, translate_text

    lexicon = Lexicon()                          # fetches + caches on first run
    result  = translate_text("dukkha nibbana", lexicon)
    print(result.translated)                     # "dissatisfaction unbinding"
"""

from .lexicon import Lexicon
from .translator import lookup_term, translate_text

__all__ = ["Lexicon", "lookup_term", "translate_text"]
