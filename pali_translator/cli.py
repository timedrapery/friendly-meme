#!/usr/bin/env python3
"""Command-line interface for the Pāli-to-contemporary-English translator.

Entry points
------------
::

    # Single-term lookup (shows definition and alternatives automatically)
    pali-translator dukkha

    # Inspect lexicon and cache state without translating text
    pali-translator --info

    # Translate a multi-word passage (token-by-token substitution)
    pali-translator --translate "dukkha samudayo nirodho maggo"

    # Add --verbose for definitions and alternative translations on passages
    pali-translator --verbose --translate "dukkha nibbana"

    # Force a fresh download of the lexicon from GitHub
    pali-translator --refresh dukkha

Exit codes
----------
0   Success (or no input — help text printed).
1   Term not found when doing a single-term lookup.
2   Lexicon loading failed.
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from dataclasses import asdict
from pathlib import Path

from .lexicon import Lexicon
from .translator import lookup_term, translate_text


class _HelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Preserve example formatting in the command help output."""


def _build_parser() -> argparse.ArgumentParser:
    """Construct and return the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="pali-translator",
        formatter_class=_HelpFormatter,
        description=(
            "Inspect and apply lexicon-governed Pāli translations from the "
            "shiny-adventure term policy."
        ),
        epilog=(
            "Examples:\n"
            "  pali-translator dukkha\n"
            "  pali-translator --info\n"
            "  pali-translator --translate \"dukkha samudayo nirodho maggo\"\n"
            "  pali-translator --verbose --translate \"dukkha nibbana\"\n"
            "  pali-translator --json --translate \"dukkha nibbana\"\n"
            "  pali-translator --cache-path ./tmp/lexicon.json --refresh dukkha"
        ),
    )
    parser.add_argument(
        "input",
        nargs="?",
        help=(
            "Pāli term or passage to inspect. Omit when using --info. "
            "Use --translate for passage mode."
        ),
    )
    parser.add_argument(
        "--translate",
        action="store_true",
        help="Treat INPUT as a multi-word passage and translate each known word.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Ignore any existing cache and rebuild the lexicon from GitHub.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show additional detail: definitions and alternative translations.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON output for scripting instead of formatted text.",
    )
    parser.add_argument(
        "--cache-path",
        type=Path,
        metavar="PATH",
        help="Read and write the lexicon cache at PATH instead of the default cache location.",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show lexicon/cache status without translating any input.",
    )
    return parser


def _print_match(match, *, verbose: bool) -> None:
    """Print a single :class:`~pali_translator.translator.TermMatch` to stdout.

    With ``verbose=False`` only the token→rendering line is printed.
    With ``verbose=True`` alternatives and the definition are also shown.
    """
    if match.untranslated_preferred:
        # Policy: this term is intentionally left in Pāli.
        print(f"  {match.token!r}  → [left in Pāli by policy]")
    else:
        print(f"  {match.token!r}  → {match.preferred_translation!r}")

    if verbose:
        if match.alternative_translations:
            print(f"    alternatives : {', '.join(match.alternative_translations)}")
        if match.definition:
            # Wrap long definitions at 72 columns for comfortable terminal reading.
            wrapped = textwrap.fill(
                match.definition,
                width=72,
                initial_indent="    ",
                subsequent_indent="    ",
            )
            print(f"    definition   :\n{wrapped}")
        if match.entry_type:
            print(f"    entry type   : {match.entry_type}")


def _emit_json(payload: dict) -> None:
    """Serialize *payload* to stdout as UTF-8 JSON."""
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _lookup_payload(query: str, match) -> dict:
    """Return a structured payload for single-term lookup results."""
    return {
        "mode": "lookup",
        "query": query,
        "found": match is not None,
        "match": asdict(match) if match is not None else None,
    }


def _translate_payload(result) -> dict:
    """Return a structured payload for passage translation results."""
    return {
        "mode": "translate",
        **asdict(result),
    }


def _info_payload(lexicon: Lexicon) -> dict:
    """Return a structured payload for lexicon status inspection."""
    return {
        "mode": "info",
        **lexicon.info(),
        "cache_warning": lexicon.cache_warning,
    }


def main(argv: list[str] | None = None) -> int:
    """Parse *argv* and run the requested translation action.

    Parameters
    ----------
    argv:
        Argument list (defaults to ``sys.argv[1:]`` when ``None``).

    Returns
    -------
    int
        Shell exit code: 0 for success, 1 when a single-term lookup fails,
        2 when the lexicon could not be loaded.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.input and not args.info:
        parser.print_help()
        return 0

    try:
        print(
            "Loading lexicon... (first run may take a moment while the cache is built)",
            file=sys.stderr,
        )
        lexicon = Lexicon(cache_path=args.cache_path, refresh=args.refresh)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    source_label = "cache" if lexicon.loaded_from_cache else "download"
    print(f"Loaded lexicon: {len(lexicon)} entries ({source_label}).", file=sys.stderr)
    if args.cache_path is not None:
        print(f"Cache path: {lexicon.cache_path}", file=sys.stderr)
    if lexicon.cache_warning:
        print(f"Warning: {lexicon.cache_warning}", file=sys.stderr)

    if args.translate:
        # --- Passage mode: translate every token in the input string ---
        result = translate_text(args.input, lexicon)
        if args.json:
            _emit_json(_translate_payload(result))
            return 0
        print(f"Original   : {result.original}")
        print(f"Translated : {result.translated}\n")
        if result.matches:
            print("Resolved terms:")
            for match in result.matches:
                _print_match(match, verbose=args.verbose)
        if result.unknown_tokens:
            print(f"\nUnresolved tokens: {', '.join(result.unknown_tokens)}")
    elif args.info:
        info = _info_payload(lexicon)
        if args.json:
            _emit_json(info)
            return 0
        print("Lexicon status:")
        print(f"  entries          : {info['entries']}")
        print(f"  cache path       : {info['cache_path']}")
        print(f"  loaded from cache: {info['loaded_from_cache']}")
        print(f"  cache exists     : {info['cache_exists']}")
        if info["cache_warning"]:
            print(f"  cache warning    : {info['cache_warning']}")
    else:
        # --- Single-term mode: look up one word and show full detail ---
        match = lookup_term(args.input, lexicon)
        if args.json:
            _emit_json(_lookup_payload(args.input, match))
            return 0 if match is not None else 1
        if match is None:
            print(f"Term {args.input!r} not found in the lexicon.")
            return 1
        _print_match(match, verbose=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
