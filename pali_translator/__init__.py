"""Pali-to-contemporary-English translator using the shiny-adventure lexicon."""

from .lexicon import Lexicon
from .translator import translate_text, lookup_term

__all__ = ["Lexicon", "translate_text", "lookup_term"]
