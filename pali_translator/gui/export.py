"""Export and report generation for Pāli translator sessions.

All functions here are pure Python with no tkinter dependency.
They consume a :class:`~pali_translator.gui.controller.TranslationSession`
and return a string suitable for writing to a file.

Supported formats
-----------------
plain text
    Human-readable report: source, translation, per-token analysis, unknowns.
JSON
    Machine-readable record including all match metadata and session metadata.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .controller import TranslationSession


def export_json(session: "TranslationSession") -> str:
    """Serialize *session* to a JSON string suitable for file export.

    The JSON record includes source text, translated text, full per-token
    match metadata, unknown tokens, lexicon source, cache path, and timestamp.
    """
    data = {
        "timestamp": session.timestamp,
        "source_text": session.source_text,
        "translated_text": session.result.translated,
        "lexicon_source": "cache" if session.lexicon_status.from_cache else "network",
        "cache_path": session.lexicon_status.cache_path,
        "token_count": len(session.token_rows),
        "match_count": len(session.result.matches),
        "unknown_count": len(session.result.unknown_tokens),
        "matches": [
            {
                "token": m.token,
                "preferred_translation": m.preferred_translation,
                "alternative_translations": m.alternative_translations,
                "definition": m.definition,
                "entry_type": m.entry_type,
                "untranslated_preferred": m.untranslated_preferred,
            }
            for m in session.result.matches
        ],
        "unknown_tokens": session.result.unknown_tokens,
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def export_plain_text(session: "TranslationSession") -> str:
    """Serialize *session* to a human-readable plain-text report."""
    source_label = (
        "cache" if session.lexicon_status.from_cache else "network download"
    )
    lines: list[str] = [
        "Pāli Translation Report",
        "=======================",
        f"Generated : {session.timestamp}",
        f"Lexicon   : {source_label}  ({session.lexicon_status.entry_count} entries)",
        f"Cache     : {session.lexicon_status.cache_path}",
        "",
        "SOURCE",
        "------",
        session.source_text,
        "",
        "TRANSLATION",
        "-----------",
        session.result.translated,
        "",
        "TOKEN ANALYSIS",
        "--------------",
    ]

    for row in session.token_rows:
        if row.matched:
            if row.untranslated_preferred:
                status = "[kept in Pāli by policy]"
            else:
                status = f"→  {row.preferred_translation}"
            token_col = f"{row.token!r:22s}"
            lines.append(f"  {token_col}  {status}")
            if row.entry_type:
                lines.append(f"    type          : {row.entry_type}")
            if row.definition:
                lines.append(f"    definition    : {row.definition}")
            if row.alternatives:
                lines.append(f"    alternatives  : {', '.join(row.alternatives)}")
        else:
            lines.append(f"  {row.token!r:22s}  [NOT IN LEXICON]")

    if session.result.unknown_tokens:
        lines += [
            "",
            "UNKNOWN TOKENS",
            "--------------",
        ]
        for tok in session.result.unknown_tokens:
            lines.append(f"  {tok!r}")

    return "\n".join(lines)
