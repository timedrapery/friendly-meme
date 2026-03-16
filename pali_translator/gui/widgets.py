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


# ---------------------------------------------------------------------------
# FilterBar
# ---------------------------------------------------------------------------

class FilterBar(tk.Frame):
    """Compact bar above the token table offering free-text search and mode buttons.

    The bar emits a virtual event ``<<FilterChanged>>`` on *parent* whenever
    the filter state changes.  Callers read :attr:`text` and :attr:`mode`
    to repopulate the table.
    """

    MODES = ("all", "matched", "unknown", "policy")
    MODE_LABELS = {"all": "All", "matched": "Matched", "unknown": "Unknown", "policy": "In Pāli"}

    def __init__(self, parent: tk.Widget, **kw: object) -> None:
        super().__init__(parent, bg=PAL_BG, **kw)
        self._mode = tk.StringVar(value="all")
        self._build()

    def _build(self) -> None:
        # Free-text entry
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_change)
        tk.Label(self, text="Filter:", font=FONT_SMALL, bg=PAL_BG, fg=PAL_FG).pack(
            side="left", padx=(0, 4)
        )
        self._entry = ttk.Entry(self, textvariable=self._search_var, font=FONT_SMALL, width=18)
        self._entry.pack(side="left", padx=(0, 6))

        # Mode radio buttons
        for m in self.MODES:
            ttk.Radiobutton(
                self,
                text=self.MODE_LABELS[m],
                variable=self._mode,
                value=m,
                command=self._on_change,
            ).pack(side="left", padx=2)

        # Clear button
        ttk.Button(self, text="✕", width=2, command=self.clear).pack(side="left", padx=(6, 0))

        # Row count label
        self._count_label = tk.Label(
            self, text="", font=FONT_SMALL, bg=PAL_BG, fg=PAL_HINT, anchor="e"
        )
        self._count_label.pack(side="right", padx=(6, 0))

    def _on_change(self, *_args: object) -> None:
        self.event_generate("<<FilterChanged>>")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def text(self) -> str:
        """Current free-text search string (may be empty)."""
        return self._search_var.get()

    @property
    def mode(self) -> str:
        """Current filter mode: one of ``"all"``, ``"matched"``, ``"unknown"``, ``"policy"``."""
        return self._mode.get()

    def focus_entry(self) -> None:
        """Focus the search entry (called by keyboard shortcut Ctrl+F)."""
        self._entry.focus_set()

    def set_count(self, shown: int, total: int) -> None:
        """Update the row-count summary label."""
        if shown == total:
            self._count_label.config(text=f"{total} row{'s' if total != 1 else ''}")
        else:
            self._count_label.config(text=f"{shown} / {total}")

    def clear(self) -> None:
        """Reset the filter to its default (empty text, mode = all)."""
        self._search_var.set("")
        self._mode.set("all")
        self.event_generate("<<FilterChanged>>")


# ---------------------------------------------------------------------------
# ConcordancePanel
# ---------------------------------------------------------------------------

class ConcordancePanel(tk.Frame):
    """Sortable table showing unique terms and their frequency in a passage.

    Each row corresponds to one :class:`~pali_translator.gui.concordance.ConcordanceEntry`.
    Clicking a column heading re-sorts in place.
    """

    COLUMNS = (
        ("normalized",   "Normalised",    110),
        ("token",        "Token",          90),
        ("count",        "Count",          52),
        ("preferred",    "Preferred",     130),
        ("type",         "Type",           60),
        ("policy",       "In Pāli?",       70),
    )

    _SORT_MAPS = {
        "count":      "frequency",
        "normalized": "alpha",
        "token":      "alpha",
    }

    def __init__(self, parent: tk.Widget, **kw: object) -> None:
        super().__init__(parent, bg=PAL_PANEL, **kw)
        self._sort_mode = "frequency"
        self._build()

    def _build(self) -> None:
        col_ids = [c[0] for c in self.COLUMNS]
        self._tree = ttk.Treeview(self, columns=col_ids, show="headings", selectmode="browse")
        for col_id, label, width in self.COLUMNS:
            self._tree.heading(col_id, text=label, command=lambda c=col_id: self._on_heading(c))
            self._tree.column(col_id, width=width, minwidth=40, stretch=False)

        self._tree.tag_configure("matched", foreground=PAL_MATCHED)
        self._tree.tag_configure("unknown", foreground=PAL_UNKNOWN)
        self._tree.tag_configure("kept",    foreground=PAL_KEPT)

        vsb = ttk.Scrollbar(self, orient="vertical",   command=self._tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Empty-state label (shown when no data yet)
        self._empty = tk.Label(
            self, text="Translate a passage to see the concordance.",
            font=FONT_SMALL, bg=PAL_PANEL, fg=PAL_HINT,
        )

    def _on_heading(self, col_id: str) -> None:
        """Re-sort on heading click, cycling through relevant sort modes."""
        new_mode = self._SORT_MAPS.get(col_id, "frequency")
        if new_mode == self._sort_mode and col_id == "count":
            new_mode = "appearance"  # toggle count ↔ appearance
        self._sort_mode = new_mode
        # Re-request sort from the app via a virtual event.
        self.event_generate("<<ConcordanceSortChanged>>")

    @property
    def sort_mode(self) -> str:
        """Current sort mode string (``"frequency"``, ``"alpha"``, or ``"appearance"``)."""
        return self._sort_mode

    def populate(self, entries: list) -> None:
        """Populate the table from a list of :class:`~pali_translator.gui.concordance.ConcordanceEntry` objects."""
        self._tree.delete(*self._tree.get_children())
        self._empty.place_forget()

        if not entries:
            self._empty.place(relx=0.5, rely=0.5, anchor="center")
            return

        for entry in entries:
            if entry.matched:
                tag = "kept" if entry.untranslated_preferred else "matched"
            else:
                tag = "unknown"
            policy = "yes" if entry.untranslated_preferred else ""
            self._tree.insert(
                "",
                "end",
                values=(
                    entry.normalized,
                    entry.representative_token,
                    entry.count,
                    entry.preferred_translation,
                    entry.entry_type,
                    policy,
                ),
                tags=(tag,),
            )

    def clear(self) -> None:
        """Clear all rows and show the empty-state label."""
        self._tree.delete(*self._tree.get_children())
        self._empty.place(relx=0.5, rely=0.5, anchor="center")

    def show_empty_state(self) -> None:
        """Show just the empty-state hint label."""
        self.clear()


# ---------------------------------------------------------------------------
# InterlinearView
# ---------------------------------------------------------------------------

class InterlinearView(tk.Frame):
    """Read-only interlinear display: token above, gloss below, phrase brackets.

    Renders a list of :class:`~pali_translator.gui.interlinear.InterlinearUnit` objects
    as a flowing grid of token/gloss cells.  Phrase-start cells span their
    phrase visually with a coloured bracket label.
    """

    _CELL_WIDTH = 110
    _CELL_PAD_X = 4
    _CELL_PAD_Y = 2

    def __init__(self, parent: tk.Widget, **kw: object) -> None:
        super().__init__(parent, bg=PAL_BG, **kw)
        self._canvas = tk.Canvas(self, bg=PAL_BG, highlightthickness=0)
        self._vsb = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._vsb.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        self._vsb.pack(side="right", fill="y")

        self._inner = tk.Frame(self._canvas, bg=PAL_BG)
        self._window = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")
        self._inner.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        # Empty state
        self._empty = tk.Label(
            self._inner,
            text="Translate a passage to see the interlinear view.",
            font=FONT_SMALL, bg=PAL_BG, fg=PAL_HINT,
        )
        self._empty.pack(padx=12, pady=20)

    def _on_inner_configure(self, _e: object) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, e: object) -> None:
        self._canvas.itemconfig(self._window, width=e.width)  # type: ignore[union-attr]

    def populate(self, units: list) -> None:
        """Render *units* (list of :class:`~pali_translator.gui.interlinear.InterlinearUnit`)."""
        for child in self._inner.winfo_children():
            child.destroy()

        if not units:
            tk.Label(
                self._inner,
                text="Translate a passage to see the interlinear view.",
                font=FONT_SMALL, bg=PAL_BG, fg=PAL_HINT,
            ).pack(padx=12, pady=20)
            return

        # Wrap cells into rows of ~8 units for readability.
        wrap = 8
        chunks = [units[i:i + wrap] for i in range(0, len(units), wrap)]
        for chunk in chunks:
            row_frame = tk.Frame(self._inner, bg=PAL_BG)
            row_frame.pack(fill="x", padx=6, pady=self._CELL_PAD_Y)
            for unit in chunk:
                self._make_cell(row_frame, unit)

    def _make_cell(self, parent: tk.Widget, unit: object) -> None:
        """Build one token/gloss cell."""
        # Colour selection
        if unit.matched:  # type: ignore[union-attr]
            fg_token = PAL_KEPT if unit.untranslated_preferred else PAL_MATCHED  # type: ignore[union-attr]
        else:
            fg_token = PAL_UNKNOWN

        cell = tk.Frame(parent, bg=PAL_PANEL, relief="groove", bd=1)
        cell.pack(side="left", padx=self._CELL_PAD_X, pady=self._CELL_PAD_Y)

        tk.Label(
            cell,
            text=unit.token,  # type: ignore[union-attr]
            font=FONT_BODY,
            bg=PAL_PANEL,
            fg=fg_token,
            width=9,
            anchor="center",
        ).pack()
        tk.Label(
            cell,
            text=unit.gloss,  # type: ignore[union-attr]
            font=FONT_SMALL,
            bg=PAL_PANEL,
            fg=PAL_FG,
            width=9,
            anchor="center",
        ).pack()

        # Phrase bracket on start cell
        if unit.is_phrase_start and unit.phrase_rendering:  # type: ignore[union-attr]
            tk.Label(
                cell,
                text=f"[{unit.phrase_rendering}]",  # type: ignore[union-attr]
                font=("TkDefaultFont", 8, "italic"),
                bg=PAL_PANEL,
                fg=PAL_ACCENT,
                wraplength=self._CELL_WIDTH,
            ).pack()

    def clear(self) -> None:
        """Remove all rendered units and show the empty-state hint."""
        for child in self._inner.winfo_children():
            child.destroy()
        tk.Label(
            self._inner,
            text="Translate a passage to see the interlinear view.",
            font=FONT_SMALL, bg=PAL_BG, fg=PAL_HINT,
        ).pack(padx=12, pady=20)
