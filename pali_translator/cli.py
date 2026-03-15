#!/usr/bin/env python3
"""Command-line interface for the Pali-to-contemporary-English translator.

Usage examples
--------------
Look up a single term::

    python -m pali_translator dukkha

Translate a passage::

    python -m pali_translator --translate "dukkha samudayo nirodho maggo"

Refresh the local lexicon cache::

    python -m pali_translator --refresh dukkha
"""

from __future__ import annotations

import argparse
import sys
import textwrap

from .lexicon import Lexicon
from .translator import lookup_term, translate_text


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pali_translator",
        description="Translate Pali terms to contemporary English using the shiny-adventure lexicon.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Pali term or passage to translate (use --translate for multi-word passages).",
    )
    parser.add_argument(
        "--translate",
        action="store_true",
        help="Treat INPUT as a multi-word passage and translate each known word.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force a fresh download of the lexicon from GitHub before translating.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show additional detail such as definitions and alternative translations.",
    )
    return parser


def _print_match(match, *, verbose: bool) -> None:
    if match.untranslated_preferred:
        print(f"  {match.token!r}  → [left in Pāli by policy]")
    else:
        print(f"  {match.token!r}  → {match.preferred_translation!r}")
    if verbose:
        if match.alternative_translations:
            print(f"    alternatives : {', '.join(match.alternative_translations)}")
        if match.definition:
            wrapped = textwrap.fill(match.definition, width=72, initial_indent="    ", subsequent_indent="    ")
            print(f"    definition   :\n{wrapped}")
        if match.entry_type:
            print(f"    entry type   : {match.entry_type}")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.input:
        parser.print_help()
        return 0

    print("Loading lexicon… (this may take a moment on first run while the cache is built)")
    lexicon = Lexicon(refresh=args.refresh)
    print(f"Lexicon loaded: {len(lexicon)} entries\n")

    if args.translate:
        result = translate_text(args.input, lexicon)
        print(f"Original   : {result.original}")
        print(f"Translated : {result.translated}\n")
        if result.matches:
            print("Resolved terms:")
            for match in result.matches:
                _print_match(match, verbose=args.verbose)
        if result.unknown_tokens:
            print(f"\nUnresolved tokens: {', '.join(result.unknown_tokens)}")
    else:
        match = lookup_term(args.input, lexicon)
        if match is None:
            print(f"Term {args.input!r} not found in the lexicon.")
            return 1
        _print_match(match, verbose=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
