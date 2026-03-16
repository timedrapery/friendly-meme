"""Custom Tkinter widget components for the Pāli translator workbench.

Each class is self-contained and composed into :class:`~pali_translator.gui.app.App`.
No application state lives here — these are pure presentation components.

Design palette
--------------
The colours and fonts aim for a warm, document-like readability that suits
scholarly text work.  Constants are exposed so :mod:`pali_translator.gui.app`
can import and use them for consistent styling across widgets it builds inline.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

# ---------------------------------------------------------------------------
# Shared design tokens
# ---------------------------------------------------------------------------

FONT_BODY  = ("Georgia", 12)
FONT_MONO  = ("Courier New", 11)
FONT_SMALL = ("TkDefaultFont", 10)
FONT_LABEL = ("TkDefaultFont", 10, "bold")

PAL_BG      = "#FAFAF7"   # main background
PAL_PANEL   = "#F2F0EB"   # inset panel background
PAL_ACCENT  = "#4A6741"   # green — matched / selected
PAL_UNKNOWN = "#B5351A"   # red — unknown tokens
PAL_KEPT    = "#8B6914"   # amber — kept-in-Pāli terms
PAL_MATCHED = "#1E5C1E"   # dark green — matched translations
PAL_FG      = "#1C1C1C"   # default foreground
PAL_HINT    = "#AAAAAA"   # placeholder text


# ---------------------------------------------------------------------------
# TokenTable
# ---------------------------------------------------------------------------

class TokenTable(tk.Frame):
    """ttk.Treeview table showing per-token workbench analysis results.

    Columns: Token · Normalized · Status · Preferred · Type · In Pāli? ·
             Definition · Alternatives

    Rows are colour-tagged:
    - green  → matched, translated
    - amber  → matched, kept in Pāli by policy
    - red    → not found in lexicon
    """

    COLUMNS = (
        ("token",        "Token",        110),
        ("normalized",   "Normalized",   100),
        ("status",       "Status",        80),
        ("preferred",    "Preferred",    140),
        ("type",         "Type",          60),
        ("policy",       "In Pāli?",      70),
        ("definition",   "Definition",   240),
        ("alternatives", "Alternatives", 150),
    )

    def __init__(self, parent: tk.Widget, **kw: object) -> None:
        super().__init__(parent, bg=PAL_PANEL, **kw)
        self._build()

    def _build(self) -> None:
        col_ids = [c[0] for c in self.COLUMNS]
        self._tree = ttk.Treeview(
            self,
            columns=col_ids,
            show="headings",
            selectmode="browse",
        )
        for col_id, label, width in self.COLUMNS:
            self._tree.heading(col_id, text=label)
            self._tree.column(col_id, width=width, minwidth=40, stretch=False)

        # Row colour tags
        self._tree.tag_configure("matched",  foreground=PAL_MATCHED)
        self._tree.tag_configure("unknown",  foreground=PAL_UNKNOWN)
        self._tree.tag_configure("kept",     foreground=PAL_KEPT)

        vsb = ttk.Scrollbar(self, orient="vertical",   command=self._tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0,  column=1, sticky="ns")
        hsb.grid(row=1,  column=0, sticky="ew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def populate(self, rows: list) -> None:
        """Clear the table and fill it from a list of :class:`~pali_translator.gui.controller.TokenRow`."""
        self._tree.delete(*self._tree.get_children())
        for row in rows:
            if row.matched:
                tag = "kept" if row.untranslated_preferred else "matched"
                policy = "yes" if row.untranslated_preferred else ""
            else:
                tag = "unknown"
                policy = ""

            defn = row.definition
            if len(defn) > 80:
                defn = defn[:79] + "…"

            alts = ", ".join(row.alternatives[:3]) if row.alternatives else ""

            self._tree.insert(
                "",
                "end",
                values=(
                    row.token,
                    row.normalized,
                    "matched" if row.matched else "UNKNOWN",
                    row.preferred_translation,
                    row.entry_type,
                    policy,
                    defn,
                    alts,
                ),
                tags=(tag,),
            )

    def clear(self) -> None:
        """Remove all rows from the table."""
        self._tree.delete(*self._tree.get_children())

    def bind_select(self, callback: Callable) -> None:
        """Attach *callback* to Treeview row-selection events."""
        self._tree.bind("<<TreeviewSelect>>", callback)

    def selected_token(self) -> str | None:
        """Return the raw token string of the currently selected row, or ``None``."""
        sel = self._tree.selection()
        if not sel:
            return None
        values = self._tree.item(sel[0], "values")
        return values[0] if values else None


# ---------------------------------------------------------------------------
# TermInspectorFrame
# ---------------------------------------------------------------------------

class TermInspectorFrame(tk.Frame):
    """Panel for displaying a single Pāli term's full lexicon record.

    Shows: headword, preferred translation, policy flag, alternatives,
    entry type, and definition.  Designed to update in-place as the user
    selects rows in the token table or performs lookups.
    """

    def __init__(self, parent: tk.Widget, **kw: object) -> None:
        super().__init__(parent, bg=PAL_PANEL, pady=2, padx=2, **kw)
        self._build()

    def _build(self) -> None:
        header = tk.Frame(self, bg=PAL_PANEL)
        header.pack(fill="x", pady=(0, 2))
        tk.Label(
            header, text="Term Inspector", font=FONT_LABEL,
            bg=PAL_PANEL, fg=PAL_FG,
        ).pack(side="left")
        tk.Button(
            header, text="✕", font=FONT_SMALL, bg=PAL_PANEL,
            relief="flat", cursor="hand2", command=self.clear,
        ).pack(side="right")

        self._text = tk.Text(
            self,
            font=FONT_SMALL,
            bg=PAL_BG,
            fg=PAL_FG,
            relief="flat",
            state="disabled",
            wrap="word",
            height=9,
            cursor="arrow",
        )
        self._text.pack(fill="both", expand=True)

        # Text tags for styled rendering
        self._text.tag_configure("heading",  font=("TkDefaultFont", 11, "bold"), foreground=PAL_ACCENT)
        self._text.tag_configure("key",      font=("TkDefaultFont", 10, "bold"))
        self._text.tag_configure("value",    font=("TkDefaultFont", 10))
        self._text.tag_configure("policy",   foreground=PAL_KEPT,    font=("TkDefaultFont", 10, "bold"))
        self._text.tag_configure("unknown",  foreground=PAL_UNKNOWN, font=("TkDefaultFont", 10))
        self._text.tag_configure("hint",     foreground=PAL_HINT,    font=("TkDefaultFont", 10, "italic"))

    # ------------------------------------------------------------------
    # Internal writer helper
    # ------------------------------------------------------------------

    def _write(self, text: str, tag: str = "value") -> None:
        self._text.insert("end", text, tag)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_match(self, match: object) -> None:
        """Display a :class:`~pali_translator.translator.TermMatch` in the inspector."""
        self._text.config(state="normal")
        self._text.delete("1.0", "end")

        self._write(f"{match.token}\n", "heading")  # type: ignore[attr-defined]

        self._write("Preferred   : ", "key")
        if match.untranslated_preferred:  # type: ignore[attr-defined]
            self._write(f"{match.preferred_translation}  ", "value")  # type: ignore[attr-defined]
            self._write("[kept in Pāli by policy]\n", "policy")
        else:
            self._write(f"{match.preferred_translation}\n", "value")  # type: ignore[attr-defined]

        if match.alternative_translations:  # type: ignore[attr-defined]
            self._write("Alternatives: ", "key")
            self._write(", ".join(match.alternative_translations) + "\n", "value")  # type: ignore[attr-defined]

        if match.entry_type:  # type: ignore[attr-defined]
            self._write("Type        : ", "key")
            self._write(f"{match.entry_type}\n", "value")  # type: ignore[attr-defined]

        if match.definition:  # type: ignore[attr-defined]
            self._write("Definition  :\n", "key")
            self._write(f"  {match.definition}\n", "value")  # type: ignore[attr-defined]

        self._text.config(state="disabled")

    def show_not_found(self, term: str) -> None:
        """Display a 'not in lexicon' message for *term*."""
        self._text.config(state="normal")
        self._text.delete("1.0", "end")
        self._write(f"\u201c{term}\u201d ", "heading")
        self._write("is not in the lexicon.\n\n", "unknown")
        self._write(
            "Unknown tokens are passed through unchanged in the translation. "
            "This may be a proper noun, an unrecognised grammatical form, or a "
            "term not yet covered by the shiny-adventure policy.",
            "hint",
        )
        self._text.config(state="disabled")

    def show_empty_state(self) -> None:
        """Display an instructional empty-state prompt."""
        self._text.config(state="normal")
        self._text.delete("1.0", "end")
        self._write(
            "Enter a term above and click Lookup,\n"
            "or click a row in the Token Analysis table.",
            "hint",
        )
        self._text.config(state="disabled")

    def clear(self) -> None:
        """Clear the inspector panel."""
        self._text.config(state="normal")
        self._text.delete("1.0", "end")
        self._text.config(state="disabled")


# ---------------------------------------------------------------------------
# StatusBar
# ---------------------------------------------------------------------------

class StatusBar(tk.Frame):
    """Single-line status bar displayed at the bottom of the main window."""

    def __init__(self, parent: tk.Widget, **kw: object) -> None:
        super().__init__(parent, bg="#E8E6E0", relief="sunken", bd=1, **kw)
        self._label = tk.Label(
            self,
            text="Starting up…",
            font=FONT_SMALL,
            bg="#E8E6E0",
            fg=PAL_FG,
            anchor="w",
            padx=6,
        )
        self._label.pack(side="left", fill="x", expand=True)

    def set(self, message: str) -> None:
        """Update the bar with a neutral informational message."""
        self._label.config(text=message, fg=PAL_FG)

    def set_ok(self, message: str) -> None:
        """Update the bar with a success-tone message."""
        self._label.config(text=message, fg=PAL_FG)

    def set_error(self, message: str) -> None:
        """Update the bar with an error-tone message (shown in red)."""
        self._label.config(text=message, fg=PAL_UNKNOWN)
