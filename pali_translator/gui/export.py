"""Export and report generation for Pāli translator sessions.

All functions here are pure Python with no tkinter dependency.
They consume a :class:`~pali_translator.gui.controller.TranslationSession`
and return a string suitable for writing to a file.

Supported formats
-----------------
plain text
    Human-readable report: source, translation, per-token analysis, unknowns.
JSON
    Machine-readable record including all match metadata, phrase matches,
    editorial notes, and session metadata.
Markdown
    GitHub-flavoured Markdown suitable for pasting into wikis, issues, or
    review documents.  Includes an analysis table and optional notes.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .controller import TranslationSession
    from .notes import NotesStore
    from ..phrases import PhraseMatch


def export_json(
    session: "TranslationSession",
    phrase_matches: "list[PhraseMatch] | None" = None,
    notes: "NotesStore | None" = None,
) -> str:
    """Serialize *session* to a JSON string suitable for file export.

    The JSON record includes source text, translated text, full per-token
    match metadata, unknown tokens, lexicon source, cache path, and timestamp.
    When *phrase_matches* and/or *notes* are supplied they are included under
    ``"phrase_matches"`` and ``"notes"`` keys respectively.
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
    # Include phrase matches when supplied (fallback to session attribute).
    pm_list = phrase_matches if phrase_matches is not None else getattr(session, "phrase_matches", [])
    if pm_list:
        data["phrase_matches"] = [
            {
                "span": list(pm.span),
                "normalized_span": list(pm.normalized_span),
                "start_pos": pm.start_pos,
                "end_pos": pm.end_pos,
                "preferred_rendering": pm.preferred_rendering,
                "entry_type": pm.entry_type,
                "untranslated_preferred": pm.untranslated_preferred,
                "source_key": pm.source_key,
            }
            for pm in pm_list
        ]

    # Include notes when supplied.
    if notes is not None and not notes.is_empty():
        data["notes"] = notes.to_dict()

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


def export_markdown(
    session: "TranslationSession",
    phrase_matches: "list[PhraseMatch] | None" = None,
    notes: "NotesStore | None" = None,
) -> str:
    """Serialize *session* to GitHub-flavoured Markdown.

    Produces a document with:

    * Front-matter block (timestamp, lexicon source).
    * Source passage and translated passage as blockquotes.
    * A token analysis table with match status, preferred translation, and type.
    * Optional phrase-match list for multi-word entries.
    * Optional editorial notes section (session, per-token, per-phrase).
    """
    source_label = (
        "cache" if session.lexicon_status.from_cache else "network download"
    )
    lines: list[str] = [
        "# Pāli Translation Report",
        "",
        f"**Generated:** {session.timestamp}  ",
        f"**Lexicon:** {source_label} ({session.lexicon_status.entry_count} entries)  ",
        "",
        "## Source",
        "",
    ]
    for src_line in session.source_text.splitlines():
        lines.append(f"> {src_line}")
    lines.append("")

    lines += [
        "## Translation",
        "",
    ]
    for tr_line in session.result.translated.splitlines():
        lines.append(f"> {tr_line}")
    lines.append("")

    # Token analysis table
    lines += [
        "## Token Analysis",
        "",
        "| Token | Status | Preferred | Type | In Pāli? |",
        "| ----- | ------ | --------- | ---- | -------- |",
    ]
    for row in session.token_rows:
        status = "matched" if row.matched else "**UNKNOWN**"
        preferred = row.preferred_translation if row.matched else "—"
        entry_type = row.entry_type or "—"
        policy = "yes" if row.untranslated_preferred else ""
        lines.append(
            f"| {row.token} | {status} | {preferred} | {entry_type} | {policy} |"
        )
    lines.append("")

    # Phrase matches
    pm_list = phrase_matches if phrase_matches is not None else getattr(session, "phrase_matches", [])
    if pm_list:
        lines += [
            "## Phrase Matches",
            "",
            "| Phrase | Preferred Rendering | Type | In Pāli? |",
            "| ------ | ------------------- | ---- | -------- |",
        ]
        for pm in pm_list:
            phrase_text = " ".join(pm.span)
            entry_type = pm.entry_type or "—"
            policy = "yes" if pm.untranslated_preferred else ""
            lines.append(
                f"| {phrase_text} | {pm.preferred_rendering} | {entry_type} | {policy} |"
            )
        lines.append("")

    # Unknown tokens summary
    if session.result.unknown_tokens:
        lines += [
            "## Unknown Tokens",
            "",
        ]
        for tok in session.result.unknown_tokens:
            lines.append(f"- `{tok}`")
        lines.append("")

    # Notes section
    if notes is not None and not notes.is_empty():
        lines += [
            "## Notes",
            "",
        ]
        if notes.session_note:
            lines += [
                "### Session Note",
                "",
                notes.session_note,
                "",
            ]
        if notes.token_notes:
            lines += ["### Token Notes", ""]
            for norm, note in sorted(notes.token_notes.items()):
                lines.append(f"**{norm}**: {note}  ")
            lines.append("")
        if notes.phrase_notes:
            lines += ["### Phrase Notes", ""]
            for key, note in sorted(notes.phrase_notes.items()):
                lines.append(f"**{key}**: {note}  ")
            lines.append("")

    return "\n".join(lines)
