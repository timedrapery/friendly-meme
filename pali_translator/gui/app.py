"""Main Tkinter application window for the Pāli Translator Workbench.

Layout (left-to-right, top-to-bottom)
--------------------------------------
┌──────────────────────────────────────────────────────────────────────┐
│  Menu bar: File | Edit | View | Tools | Help                         │
├──────────────────────┬───────────────────────────────────────────────┤
│  LEFT PANE           │  RIGHT PANE                                   │
│  ─ [History drawer]  │  ─ Translation output   [Copy Output]         │
│  ─ Source (Pāli)     │  ─ Notebook tabs:                             │
│  ─ [Translate]       │      Token Analysis | Concordance             │
│    [Clear]           │      Interlinear    | Compare                 │
│    [Refresh Lexicon] │  ─ Notes area (collapsible)                   │
│  ─ ─ ─ ─ ─ ─ ─ ─    │                                                │
│  ─ Term Lookup       │                                                │
│  ─ Term Inspector    │                                                │
├──────────────────────┴───────────────────────────────────────────────┤
│  Status bar                                                          │
└──────────────────────────────────────────────────────────────────────┘

The left and right panes are separated by a ttk.PanedWindow so users can
resize them.  All translation logic lives in
:class:`~pali_translator.gui.controller.Controller`; this module is
responsible only for wiring Tk events to controller calls and reflecting
results back into widgets.
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .controller import Controller
from .export import export_json, export_markdown, export_plain_text
from .interlinear import build_interlinear
from .widgets import (
    FONT_BODY,
    FONT_LABEL,
    FONT_SMALL,
    PAL_ACCENT,
    PAL_BG,
    PAL_FG,
    PAL_HINT,
    PAL_PANEL,
    StatusBar,
    TermInspectorFrame,
    TokenTable,
    FilterBar,
    ConcordancePanel,
    InterlinearView,
)

_APP_TITLE   = "Pāli Translator Workbench"
_WINDOW_SIZE = "1400x860"
_MIN_W, _MIN_H = 900, 600

# Placeholder text shown in the source input when it is empty
_INPUT_HINT = "Enter a Pāli passage here…  (Ctrl+Return to translate)"

# Snapshot stored for comparison workflow
_COMPARE_SNAPSHOT_KEY = "_compare_snapshot"


class App(tk.Tk):
    """Root window of the Pāli Translator Workbench application."""

    def __init__(self) -> None:
        super().__init__()
        self.title(_APP_TITLE)
        self.geometry(_WINDOW_SIZE)
        self.minsize(_MIN_W, _MIN_H)
        self.configure(bg=PAL_BG)

        self._compare_snapshot = None  # TranslationSession stored for comparison
        self._ctrl = Controller()

        self._build_menu()
        self._build_body()
        self._build_status_bar()

        # Kick off lexicon load immediately so the user doesn't have to wait.
        self._start_lexicon_load(refresh=False)

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # File
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(
            label="Export as Plain Text…",
            command=self._export_text,
            accelerator="Ctrl+Shift+S",
        )
        file_menu.add_command(
            label="Export as JSON…",
            command=self._export_json,
        )
        file_menu.add_command(
            label="Export as Markdown…",
            command=self._export_markdown,
            accelerator="Ctrl+Shift+M",
        )
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.quit, accelerator="Ctrl+Q")
        self.bind_all("<Control-Shift-M>", lambda _e: self._export_markdown())
        self.bind_all("<Control-Shift-S>", lambda _e: self._export_text())
        self.bind_all("<Control-q>",       lambda _e: self.quit())

        # Edit
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(
            label="Copy Output",
            command=self._copy_output,
            accelerator="Ctrl+Shift+C",
        )
        self.bind_all("<Control-Shift-C>", lambda _e: self._copy_output())
        # View
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(
            label="Toggle History Panel",
            command=self._toggle_history,
            accelerator="Ctrl+H",
        )
        view_menu.add_command(
            label="Toggle Notes Panel",
            command=self._toggle_notes,
            accelerator="Ctrl+Shift+N",
        )
        self.bind_all("<Control-h>",       lambda _e: self._toggle_history())
        self.bind_all("<Control-Shift-N>", lambda _e: self._toggle_notes())
        self.bind_all("<Control-f>",       lambda _e: self._focus_filter())

        # Tools
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(
            label="Settings…",
            command=self._show_settings,
            accelerator="Ctrl+,",
        )
        tools_menu.add_separator()
        tools_menu.add_command(
            label="Snapshot for Comparison",
            command=self._snapshot_for_compare,
        )
        self.bind_all("<Control-comma>", lambda _e: self._show_settings())


        # Help
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Lexicon & Cache Info", command=self._show_cache_info)
        help_menu.add_separator()
        help_menu.add_command(label="About…", command=self._show_about)

    # ------------------------------------------------------------------
    # Body layout
    # ------------------------------------------------------------------

    def _build_body(self) -> None:
        """Build the main PanedWindow that holds left and right panes."""
        self._panes = ttk.PanedWindow(self, orient="horizontal")
        self._panes.pack(fill="both", expand=True, padx=4, pady=(4, 0))

        self._build_left_pane()
        self._build_right_pane()

    # ------------------------------------------------------------------
    # Left pane: source input + controls + term lookup + inspector
    # ------------------------------------------------------------------

    def _build_left_pane(self) -> None:
        left = tk.Frame(self._panes, bg=PAL_BG)
        self._panes.add(left, weight=4)
        # -- History drawer (collapsible) --
        self._history_visible = tk.BooleanVar(value=False)
        self._history_frame = tk.Frame(left, bg=PAL_PANEL, relief="groove", bd=1)
        # Not packed initially — toggled via _toggle_history().

        hist_header = tk.Frame(self._history_frame, bg=PAL_PANEL)
        hist_header.pack(fill="x", padx=4, pady=(2, 0))
        tk.Label(
            hist_header, text="History", font=FONT_LABEL, bg=PAL_PANEL, fg=PAL_FG, anchor="w",
        ).pack(side="left")
        ttk.Button(hist_header, text="Clear", width=5,
                   command=self._clear_history).pack(side="right")

        self._history_listbox = tk.Listbox(
            self._history_frame,
            font=FONT_SMALL,
            bg=PAL_BG,
            fg=PAL_FG,
            selectbackground=PAL_ACCENT,
            selectforeground="#FFFFFF",
            height=6,
            relief="flat",
            activestyle="none",
        )
        self._history_listbox.pack(fill="both", expand=True, padx=4, pady=(2, 4))
        self._history_listbox.bind("<Double-Button-1>", self._on_history_restore)
        self._history_listbox.bind("<Return>",          self._on_history_restore)

        ttk.Separator(left, orient="horizontal").pack(fill="x", padx=6, pady=(0, 4))


        # Section label
        tk.Label(
            left, text="Source (Pāli)", font=FONT_LABEL, bg=PAL_BG, fg=PAL_FG, anchor="w",
        ).pack(fill="x", padx=6, pady=(4, 0))

        # Input text + vertical scrollbar
        inp_frame = tk.Frame(left, bg=PAL_BG)
        inp_frame.pack(fill="x", padx=6, pady=(2, 4))
        inp_vsb = ttk.Scrollbar(inp_frame, orient="vertical")
        inp_vsb.pack(side="right", fill="y")
        self._input_text = tk.Text(
            inp_frame,
            wrap="word",
            font=FONT_BODY,
            bg=PAL_BG,
            fg=PAL_FG,
            insertbackground=PAL_FG,
            relief="solid",
            borderwidth=1,
            height=8,
            yscrollcommand=inp_vsb.set,
        )
        self._input_text.pack(side="left", fill="both", expand=True)
        inp_vsb.config(command=self._input_text.yview)

        # Keyboard shortcut: Ctrl+Return translates
        self._input_text.bind("<Control-Return>", lambda _e: self._on_translate())

        # Placeholder hint
        self._placeholder_active = True
        self._input_text.insert("1.0", _INPUT_HINT)
        self._input_text.config(fg=PAL_HINT)
        self._input_text.bind("<FocusIn>",  self._on_input_focus_in)
        self._input_text.bind("<FocusOut>", self._on_input_focus_out)

        # Button row
        btn_row = tk.Frame(left, bg=PAL_BG)
        btn_row.pack(fill="x", padx=6, pady=(0, 6))

        self._translate_btn = ttk.Button(btn_row, text="Translate", command=self._on_translate)
        self._translate_btn.pack(side="left", padx=(0, 4))

        self._clear_btn = ttk.Button(btn_row, text="Clear", command=self._on_clear)
        self._clear_btn.pack(side="left", padx=(0, 4))

        self._refresh_btn = ttk.Button(
            btn_row, text="Refresh Lexicon", command=self._on_refresh_lexicon
        )
        self._refresh_btn.pack(side="left")

        ttk.Separator(left, orient="horizontal").pack(fill="x", padx=6, pady=6)

        # Term lookup
        tk.Label(
            left, text="Term Lookup", font=FONT_LABEL, bg=PAL_BG, fg=PAL_FG, anchor="w",
        ).pack(fill="x", padx=6, pady=(0, 2))

        lookup_row = tk.Frame(left, bg=PAL_BG)
        lookup_row.pack(fill="x", padx=6, pady=(0, 4))

        self._lookup_var = tk.StringVar()
        self._lookup_entry = ttk.Entry(lookup_row, textvariable=self._lookup_var, font=FONT_BODY)
        self._lookup_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self._lookup_entry.bind("<Return>", lambda _e: self._on_lookup())

        ttk.Button(lookup_row, text="Lookup", command=self._on_lookup).pack(side="left")

        # Term inspector
        self._inspector = TermInspectorFrame(left)
        self._inspector.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self._inspector.show_empty_state()

    # ------------------------------------------------------------------
    # Right pane: translation output + token analysis table
    # ------------------------------------------------------------------

    def _build_right_pane(self) -> None:
        right = tk.Frame(self._panes, bg=PAL_BG)
        self._panes.add(right, weight=6)

        # Output header row
        out_header = tk.Frame(right, bg=PAL_BG)
        out_header.pack(fill="x", padx=6, pady=(4, 0))
        tk.Label(
            out_header, text="Translation", font=FONT_LABEL, bg=PAL_BG, fg=PAL_FG, anchor="w",
        ).pack(side="left")
        ttk.Button(
            out_header, text="Copy Output", command=self._copy_output,
        ).pack(side="right")

        # Output text + scrollbar
        out_frame = tk.Frame(right, bg=PAL_BG)
        out_frame.pack(fill="x", padx=6, pady=(2, 4))
        out_vsb = ttk.Scrollbar(out_frame, orient="vertical")
        out_vsb.pack(side="right", fill="y")
        self._output_text = tk.Text(
            out_frame,
            wrap="word",
            font=FONT_BODY,
            bg=PAL_BG,
            fg=PAL_FG,
            relief="solid",
            borderwidth=1,
            state="disabled",
            height=7,
            cursor="arrow",
            yscrollcommand=out_vsb.set,
        )
        self._output_text.pack(side="left", fill="both", expand=True)
        out_vsb.config(command=self._output_text.yview)

        ttk.Separator(right, orient="horizontal").pack(fill="x", padx=6, pady=4)
        # Unknown-token summary lives above the notebook
        sum_row = tk.Frame(right, bg=PAL_BG)
        sum_row.pack(fill="x", padx=6, pady=(0, 2))
        self._unknown_label = tk.Label(
            sum_row, text="", font=FONT_SMALL, bg=PAL_BG, fg="#B5351A", anchor="e",
        )
        self._unknown_label.pack(side="right", fill="x", expand=True)
        # Notebook with analysis tabs (fills remaining vertical space)
        self._notebook = ttk.Notebook(right)
        self._notebook.pack(fill="both", expand=True, padx=6, pady=(0, 2))

        self._build_tab_token_analysis()
        self._build_tab_concordance()
        self._build_tab_interlinear()
        self._build_tab_compare()

        # Notes area (collapsible, below the notebook)
        self._notes_visible = tk.BooleanVar(value=False)
        self._notes_frame = tk.Frame(right, bg=PAL_PANEL, relief="groove", bd=1)
        # Not packed initially — toggled via _toggle_notes().

        notes_header = tk.Frame(self._notes_frame, bg=PAL_PANEL)
        notes_header.pack(fill="x", padx=4, pady=(2, 0))
        tk.Label(
            notes_header, text="Session Note", font=FONT_LABEL, bg=PAL_PANEL, fg=PAL_FG,
        ).pack(side="left")
        ttk.Button(notes_header, text="Clear", width=5,
                   command=self._on_notes_clear).pack(side="right")

        self._notes_text = tk.Text(
            self._notes_frame,
            font=FONT_SMALL,
            bg=PAL_BG,
            fg=PAL_FG,
            insertbackground=PAL_FG,
            relief="flat",
            height=4,
            wrap="word",
        )
        self._notes_text.pack(fill="both", padx=4, pady=(2, 4))
        self._notes_text.bind("<KeyRelease>", self._on_notes_changed)

    # ------------------------------------------------------------------
    # Notebook tab builders
    # ------------------------------------------------------------------

    def _build_tab_token_analysis(self) -> None:
        tab = tk.Frame(self._notebook, bg=PAL_BG)
        self._notebook.add(tab, text="Token Analysis")

        # Filter bar
        self._filter_bar = FilterBar(tab)
        self._filter_bar.pack(fill="x", padx=4, pady=(4, 2))
        self._filter_bar.bind("<<FilterChanged>>", self._on_filter_changed)

        # Token table
        self._token_table = TokenTable(tab)
        self._token_table.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self._token_table.bind_select(self._on_table_select)

    def _build_tab_concordance(self) -> None:
        tab = tk.Frame(self._notebook, bg=PAL_BG)
        self._notebook.add(tab, text="Concordance")

        # Sort controls row
        sort_row = tk.Frame(tab, bg=PAL_BG)
        sort_row.pack(fill="x", padx=4, pady=(4, 2))
        tk.Label(sort_row, text="Sort:", font=FONT_SMALL, bg=PAL_BG, fg=PAL_FG).pack(side="left", padx=(0, 4))
        self._conc_sort_var = tk.StringVar(value=self._ctrl.settings.concordance_sort)
        for mode in ("frequency", "alpha", "appearance"):
            ttk.Radiobutton(
                sort_row, text=mode.capitalize(), variable=self._conc_sort_var,
                value=mode, command=self._on_concordance_sort_changed,
            ).pack(side="left", padx=2)

        self._concordance_panel = ConcordancePanel(tab)
        self._concordance_panel.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self._concordance_panel.bind("<<ConcordanceSortChanged>>", self._on_concordance_sort_changed)
        self._concordance_panel.show_empty_state()

    def _build_tab_interlinear(self) -> None:
        tab = tk.Frame(self._notebook, bg=PAL_BG)
        self._notebook.add(tab, text="Interlinear")
        self._interlinear_view = InterlinearView(tab)
        self._interlinear_view.pack(fill="both", expand=True, padx=4, pady=4)

    def _build_tab_compare(self) -> None:
        tab = tk.Frame(self._notebook, bg=PAL_BG)
        self._notebook.add(tab, text="Compare")

        snap_row = tk.Frame(tab, bg=PAL_BG)
        snap_row.pack(fill="x", padx=4, pady=(4, 2))
        ttk.Button(
            snap_row, text="Set Snapshot (current session)",
            command=self._snapshot_for_compare,
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            snap_row, text="Compare Snapshot ↔ Current",
            command=self._run_compare,
        ).pack(side="left")

        compare_frame = tk.Frame(tab, bg=PAL_BG)
        compare_frame.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        cmp_vsb = ttk.Scrollbar(compare_frame, orient="vertical")
        cmp_vsb.pack(side="right", fill="y")
        self._compare_text = tk.Text(
            compare_frame,
            font=FONT_SMALL,
            bg=PAL_BG,
            fg=PAL_FG,
            relief="flat",
            state="disabled",
            wrap="word",
            yscrollcommand=cmp_vsb.set,
        )
        self._compare_text.pack(side="left", fill="both", expand=True)
        cmp_vsb.config(command=self._compare_text.yview)
        self._compare_text.tag_configure("heading", font=("TkDefaultFont", 11, "bold"), foreground=PAL_ACCENT)
        self._compare_text.tag_configure("added",   foreground="#1E5C1E")
        self._compare_text.tag_configure("removed", foreground="#B5351A")
        self._compare_text.tag_configure("changed", foreground="#8B6914")
        self._compare_text.tag_configure("hint",    foreground=PAL_HINT, font=("TkDefaultFont", 10, "italic"))
        self._compare_text.config(state="normal")
        self._compare_text.insert("1.0",
            "Use the buttons above to snapshot the current session and compare\n"
            "it against a later translation of the same or similar text.",
            "hint",
        )
        self._compare_text.config(state="disabled")
        self._token_table.bind_select(self._on_table_select)

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _build_status_bar(self) -> None:
        self._status_bar = StatusBar(self)
        self._status_bar.pack(side="bottom", fill="x")

    # ------------------------------------------------------------------
    # Placeholder helpers
    # ------------------------------------------------------------------

    def _on_input_focus_in(self, _event: object) -> None:
        if self._placeholder_active:
            self._input_text.delete("1.0", "end")
            self._input_text.config(fg=PAL_FG)
            self._placeholder_active = False

    def _on_input_focus_out(self, _event: object) -> None:
        if not self._input_text.get("1.0", "end").strip():
            self._input_text.insert("1.0", _INPUT_HINT)
            self._input_text.config(fg=PAL_HINT)
            self._placeholder_active = True

    def _get_source_text(self) -> str:
        """Return the source text if it is not the placeholder."""
        if self._placeholder_active:
            return ""
        return self._input_text.get("1.0", "end").strip()

    # ------------------------------------------------------------------
    # Lexicon loading (background thread)
    # ------------------------------------------------------------------

    def _set_controls_state(self, state: str) -> None:
        for widget in (self._translate_btn, self._refresh_btn):
            widget.config(state=state)

    def _start_lexicon_load(self, refresh: bool = False) -> None:
        self._set_controls_state("disabled")
        if refresh:
            self._status_bar.set("Re-downloading lexicon from GitHub…")
        else:
            self._status_bar.set(
                "Loading lexicon… first run may take a moment while the cache is built."
            )

        def _worker() -> None:
            status = self._ctrl.load_lexicon(refresh=refresh)
            self.after(0, lambda: self._on_lexicon_loaded(status))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_lexicon_loaded(self, status: object) -> None:
        if status.loaded:  # type: ignore[attr-defined]
            source = "cache" if status.from_cache else "network download"  # type: ignore[attr-defined]
            self._status_bar.set_ok(
                f"Lexicon ready  ·  {status.entry_count} entries  ·  {source}"  # type: ignore[attr-defined]
            )
            self._set_controls_state("normal")
        else:
            self._status_bar.set_error(
                f"Lexicon failed to load: {status.error}"  # type: ignore[attr-defined]
            )
            self._set_controls_state("disabled")
            messagebox.showerror(
                "Lexicon Load Error",
                f"The lexicon could not be loaded:\n\n{status.error}\n\n"  # type: ignore[attr-defined]
                "If you are offline, the local cache must exist for the app to "
                "work. Use Refresh Lexicon once you have a network connection.",
            )

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_translate(self) -> None:
        if not self._ctrl.lexicon_ready:
            self._status_bar.set_error("Lexicon is not loaded yet — please wait.")
            return

        text = self._get_source_text()
        if not text:
            self._status_bar.set("Enter a Pāli passage in the Source field, then click Translate.")
            return

        try:
            result = self._ctrl.translate(text)
        except RuntimeError as exc:
            self._status_bar.set_error(str(exc))
            return

        # Update output text
        self._output_text.config(state="normal")
        self._output_text.delete("1.0", "end")
        self._output_text.insert("1.0", result.translated)
        self._output_text.config(state="disabled")

        # Populate token table
        session = self._ctrl.current_session
        if session is not None:
            filter_text = self._filter_bar.text
            filter_mode = self._filter_bar.mode
            visible = self._ctrl.filter_session_tokens(text=filter_text, mode=filter_mode)
            self._token_table.populate(visible)
            total = len(session.token_rows)
            self._filter_bar.set_count(len(visible), total)

            # Refresh concordance
            self._refresh_concordance()

            # Refresh interlinear
            self._refresh_interlinear(session)

            # Update history listbox
            self._refresh_history_listbox()
            self._token_table.populate(session.token_rows)

        # Unknown-token summary
        n_unknown = len(result.unknown_tokens)
        if n_unknown:
            self._unknown_label.config(
                text=f"{n_unknown} unknown token{'s' if n_unknown != 1 else ''}  ·  shown in red below"
            )
        else:
            self._unknown_label.config(text="")
        # Auto-copy setting
        if self._ctrl.settings.auto_copy:
            self.clipboard_clear()
            self.clipboard_append(result.translated)


        self._status_bar.set_ok(
            f"Translated  ·  {len(result.matches)} matched  ·  {n_unknown} unknown"
        )

    def _on_clear(self) -> None:
        # Clear input (re-show placeholder)
        self._input_text.config(fg=PAL_FG)
        self._placeholder_active = False
        self._input_text.delete("1.0", "end")
        self._on_input_focus_out(None)

        # Clear output
        self._output_text.config(state="normal")
        self._output_text.delete("1.0", "end")
        self._output_text.config(state="disabled")

        # Clear table and inspector
        self._token_table.clear()
        self._filter_bar.clear()
        self._concordance_panel.show_empty_state()
        self._interlinear_view.clear()
        self._inspector.show_empty_state()
        self._unknown_label.config(text="")
        self._status_bar.set_ok("Cleared.")

    def _on_refresh_lexicon(self) -> None:
        if messagebox.askyesno(
            "Refresh Lexicon",
            "Re-download the lexicon from GitHub?\n\n"
            "This will overwrite the local cache and requires an internet connection.",
        ):
            self._start_lexicon_load(refresh=True)

    def _on_lookup(self) -> None:
        if not self._ctrl.lexicon_ready:
            self._status_bar.set_error("Lexicon is not loaded yet.")
            return

        term = self._lookup_var.get().strip()
        if not term:
            return

        try:
            match = self._ctrl.lookup(term)
        except RuntimeError as exc:
            self._status_bar.set_error(str(exc))
            return

        if match is not None:
            self._inspector.show_match(match)
            self._status_bar.set_ok(
                f"Found: \u201c{term}\u201d  →  {match.preferred_translation!r}"
            )
        else:
            self._inspector.show_not_found(term)
            self._status_bar.set_ok(f"\u201c{term}\u201d not found in lexicon.")

    def _on_table_select(self, _event: object) -> None:
        """Clicking a token table row looks up that token in the inspector."""
        token = self._token_table.selected_token()
        if not token or not self._ctrl.lexicon_ready:
            return

        word = token.strip(".,;:!?\"'()[]{}—-")
        if not word:
            return

        try:
            match = self._ctrl.lookup(word)
        except RuntimeError:
            return

        if match is not None:
            self._inspector.show_match(match)
        else:
            self._inspector.show_not_found(word)

        self._lookup_var.set(word)
    def _on_filter_changed(self, _event: object = None) -> None:
        """Re-populate the token table when the filter bar state changes."""
        session = self._ctrl.current_session
        if session is None:
            self._filter_bar.set_count(0, 0)
            return
        rows = self._ctrl.filter_session_tokens(
            text=self._filter_bar.text,
            mode=self._filter_bar.mode,
        )
        self._token_table.populate(rows)
        self._filter_bar.set_count(len(rows), len(session.token_rows))

    def _on_concordance_sort_changed(self, _event: object = None) -> None:
        """Re-sort the concordance when the user changes the sort mode."""
        mode = self._conc_sort_var.get()
        self._ctrl.settings.concordance_sort = mode
        self._refresh_concordance(sort_mode=mode)

    def _refresh_concordance(self, sort_mode: str | None = None) -> None:
        mode = sort_mode or self._conc_sort_var.get()
        entries = self._ctrl.build_concordance(sort_mode=mode)
        self._concordance_panel.populate(entries)

    def _refresh_interlinear(self, session: object) -> None:
        rows = session.token_rows  # type: ignore[union-attr]
        phrase_matches = getattr(session, "phrase_matches", [])
        units = build_interlinear(rows, phrase_matches)
        self._interlinear_view.populate(units)


    # History panel
    # ------------------------------------------------------------------

    def _toggle_history(self) -> None:
        """Show or hide the history drawer in the left pane."""
        if self._history_visible.get():
            self._history_frame.pack_forget()
            self._history_visible.set(False)
        else:
            # Pack before the source label – find root left child
            self._history_frame.pack(
                fill="x", padx=6, pady=(4, 6), before=self._input_text.master.master
            )
            self._history_visible.set(True)
            self._refresh_history_listbox()

    def _refresh_history_listbox(self) -> None:
        self._history_listbox.delete(0, "end")
        for s in self._ctrl.history.get_all():
            snippet = s.source_text[:40].replace("\n", " ")
            label = f"{s.timestamp[:16]}  {snippet}…" if len(s.source_text) > 40 else f"{s.timestamp[:16]}  {s.source_text}"
            self._history_listbox.insert("end", label)

    def _on_history_restore(self, _event: object = None) -> None:
        idx = self._history_listbox.curselection()
        if not idx:
            return
        session = self._ctrl.history.get(idx[0])
        self._ctrl.restore_session(session)

        # Re-populate UI from the restored session
        self._output_text.config(state="normal")
        self._output_text.delete("1.0", "end")
        self._output_text.insert("1.0", session.result.translated)
        self._output_text.config(state="disabled")

        self._token_table.populate(session.token_rows)
        self._filter_bar.clear()
        self._filter_bar.set_count(len(session.token_rows), len(session.token_rows))
        self._refresh_concordance()
        self._refresh_interlinear(session)

        n_unknown = len(session.result.unknown_tokens)
        if n_unknown:
            self._unknown_label.config(
                text=f"{n_unknown} unknown token{'s' if n_unknown != 1 else ''}"
            )
        else:
            self._unknown_label.config(text="")

        # Restore source text
        self._input_text.config(fg=PAL_FG)
        self._placeholder_active = False
        self._input_text.delete("1.0", "end")
        self._input_text.insert("1.0", session.source_text)

        self._status_bar.set_ok(
            f"Restored session from {session.timestamp[:16]}."
        )

    def _clear_history(self) -> None:
        self._ctrl.history.clear()
        self._refresh_history_listbox()
        self._status_bar.set_ok("History cleared.")

    # ------------------------------------------------------------------
    # Notes panel
    # ------------------------------------------------------------------

    def _toggle_notes(self) -> None:
        """Show or hide the notes area below the notebook."""
        if self._notes_visible.get():
            self._notes_frame.pack_forget()
            self._notes_visible.set(False)
        else:
            self._notes_frame.pack(fill="x", padx=6, pady=(2, 4))
            self._notes_visible.set(True)

    def _on_notes_changed(self, _event: object = None) -> None:
        """Persist the session note into the notes store on every keystroke."""
        note = self._notes_text.get("1.0", "end").strip()
        self._ctrl.notes.set_session_note(note)

    def _on_notes_clear(self) -> None:
        self._notes_text.delete("1.0", "end")
        self._ctrl.notes.clear_session_note()

    # ------------------------------------------------------------------
    # Compare workflow
    # ------------------------------------------------------------------

    def _snapshot_for_compare(self) -> None:
        session = self._ctrl.current_session
        if session is None:
            messagebox.showinfo("No Session", "Translate some text first.")
            return
        self._compare_snapshot = session
        self._status_bar.set_ok(
            f"Snapshot saved ({session.timestamp[:16]}).  "
            "Translate another passage, then use Compare Snapshot ↔ Current."
        )

    def _run_compare(self) -> None:
        current = self._ctrl.current_session
        if self._compare_snapshot is None:
            messagebox.showinfo(
                "No Snapshot",
                "Set a snapshot first: translate a passage, then click\n"
                "'Set Snapshot (current session)' in the Compare tab or the Tools menu.",
            )
            return
        if current is None:
            messagebox.showinfo("No Current Session", "Translate some text first.")
            return
        if self._compare_snapshot is current:
            messagebox.showinfo(
                "Same Session",
                "The snapshot and current session are the same.\n"
                "Translate a new passage before comparing.",
            )
            return

        summary = self._ctrl.compare(self._compare_snapshot, current)
        self._compare_text.config(state="normal")
        self._compare_text.delete("1.0", "end")

        def w(t: str, tag: str = "") -> None:
            self._compare_text.insert("end", t, tag)

        w(f"Snapshot  : {summary.session_a_timestamp}\n", "heading")
        w(f"Current   : {summary.session_b_timestamp}\n\n", "heading")

        if not summary.has_differences:
            w("No vocabulary differences detected.\n", "hint")
        else:
            if summary.added_tokens:
                w("Added tokens (in current, not in snapshot):\n", "heading")
                for tok in summary.added_tokens:
                    w(f"  + {tok}\n", "added")
                w("\n")
            if summary.removed_tokens:
                w("Removed tokens (in snapshot, not in current):\n", "heading")
                for tok in summary.removed_tokens:
                    w(f"  − {tok}\n", "removed")
                w("\n")
            if summary.changed_tokens:
                w("Translation changes:\n", "heading")
                for diff in summary.changed_tokens:
                    w(f"  {diff.normalized}:  ", "")
                    w(f"{diff.old_translation!r} → {diff.new_translation!r}\n", "changed")
                w("\n")
            if summary.newly_matched:
                w("Newly matched (was unknown, now found):\n", "heading")
                for tok in summary.newly_matched:
                    w(f"  ✓ {tok}\n", "added")
                w("\n")
            if summary.newly_unknown:
                w("Newly unknown (was matched, now missing):\n", "heading")
                for tok in summary.newly_unknown:
                    w(f"  ✗ {tok}\n", "removed")

        self._compare_text.config(state="disabled")
        # Switch to Compare tab
        self._notebook.select(3)

    # ------------------------------------------------------------------
    # Focus helpers (keyboard shortcuts)
    # ------------------------------------------------------------------

    def _focus_filter(self) -> None:
        """Focus the filter bar entry and switch to Token Analysis tab."""
        self._notebook.select(0)
        self._filter_bar.focus_entry()

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _export_text(self) -> None:
        session = self._ctrl.current_session
        if session is None:
            messagebox.showinfo(
                "Nothing to Export",
                "Translate some text first before exporting.",
            )
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialdir=self._ctrl.settings.last_export_dir or None,
            title="Export Translation Report",
        )
        if not path:
            return

        try:
            content = export_plain_text(session)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
            self._ctrl.settings.last_export_dir = str(__import__("pathlib").Path(path).parent)
            self._ctrl.save_settings()
            self._status_bar.set_ok(f"Exported to {path}")
        except OSError as exc:
            messagebox.showerror("Export Failed", f"Could not write file:\n{exc}")

    def _export_json(self) -> None:
        session = self._ctrl.current_session
        if session is None:
            messagebox.showinfo(
                "Nothing to Export",
                "Translate some text first before exporting.",
            )
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=self._ctrl.settings.last_export_dir or None,
            title="Export Translation JSON",
        )
        if not path:
            return

        try:
            content = export_json(session, notes=self._ctrl.notes)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
            self._ctrl.settings.last_export_dir = str(__import__("pathlib").Path(path).parent)
            self._ctrl.save_settings()
            self._status_bar.set_ok(f"Exported to {path}")
        except OSError as exc:
            messagebox.showerror("Export Failed", f"Could not write file:\n{exc}")
    def _export_markdown(self) -> None:
        session = self._ctrl.current_session
        if session is None:
            messagebox.showinfo(
                "Nothing to Export",
                "Translate some text first before exporting.",
            )
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown files", "*.md"), ("All files", "*.*")],
            title="Export Translation Markdown",
            initialdir=self._ctrl.settings.last_export_dir or None,
        )
        if not path:
            return

        try:
            content = export_markdown(session, notes=self._ctrl.notes)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
            self._ctrl.settings.last_export_dir = str(__import__("pathlib").Path(path).parent)
            self._ctrl.save_settings()
            self._status_bar.set_ok(f"Exported to {path}")
        except OSError as exc:
            messagebox.showerror("Export Failed", f"Could not write file:\n{exc}")


    def _copy_output(self) -> None:
        text = self._output_text.get("1.0", "end").strip()
        if not text:
            self._status_bar.set("Nothing to copy — translate some text first.")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self._status_bar.set_ok("Output copied to clipboard.")
    # ------------------------------------------------------------------
    # Settings dialog
    # ------------------------------------------------------------------

    def _show_settings(self) -> None:
        """Open a simple settings dialog."""
        dlg = tk.Toplevel(self)
        dlg.title("Settings")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.configure(bg=PAL_BG)

        s = self._ctrl.settings
        fields: list[tuple[str, str, tk.Variable]] = []

        def _row(label: str, field_name: str, var: tk.Variable) -> None:
            r = tk.Frame(dlg, bg=PAL_BG)
            r.pack(fill="x", padx=16, pady=4)
            tk.Label(r, text=label, width=20, anchor="w", font=FONT_SMALL, bg=PAL_BG, fg=PAL_FG).pack(side="left")
            if isinstance(var, tk.BooleanVar):
                ttk.Checkbutton(r, variable=var).pack(side="left")
            else:
                ttk.Entry(r, textvariable=var, width=18, font=FONT_SMALL).pack(side="left")
            fields.append((label, field_name, var))

        font_var = tk.IntVar(value=s.font_size)
        hist_var = tk.IntVar(value=s.history_size)
        sort_var = tk.StringVar(value=s.concordance_sort)
        copy_var = tk.BooleanVar(value=s.auto_copy)

        _row("Font size (8–24):",      "font_size",       font_var)
        _row("History size (1–100):",  "history_size",    hist_var)
        _row("Concordance sort:",      "concordance_sort", sort_var)
        _row("Auto-copy translation:", "auto_copy",       copy_var)

        def _apply() -> None:
            try:
                s.font_size       = max(8,  min(24,  int(font_var.get())))
                s.history_size    = max(1,  min(100, int(hist_var.get())))
            except (ValueError, tk.TclError):
                messagebox.showerror("Invalid Value", "Font size and history size must be whole numbers.", parent=dlg)
                return
            s.concordance_sort = sort_var.get() if sort_var.get() in ("frequency", "alpha", "appearance") else "frequency"
            s.auto_copy        = bool(copy_var.get())
            self._ctrl.history.maxlen = s.history_size
            self._conc_sort_var.set(s.concordance_sort)
            self._ctrl.save_settings()
            dlg.destroy()
            self._status_bar.set_ok("Settings saved.")

        btn_row = tk.Frame(dlg, bg=PAL_BG)
        btn_row.pack(padx=16, pady=(8, 12))
        ttk.Button(btn_row, text="Apply", command=_apply).pack(side="left", padx=(0, 6))
        ttk.Button(btn_row, text="Cancel", command=dlg.destroy).pack(side="left")

        dlg.wait_window()


    # ------------------------------------------------------------------
    # Info dialogs
    # ------------------------------------------------------------------

    def _show_about(self) -> None:
        from .. import __version__
        messagebox.showinfo(
            "About Pāli Translator Workbench",
            f"Pāli Translator Workbench  v{__version__}\n\n"
            "A lexicon-governed Pāli translation tool built on the\n"
            "timedrapery/shiny-adventure term policy.\n\n"
            "Translates token by token using explicit editorial policy —\n"
            "no machine learning, no guessed renderings.\n"
            "Unknown terms are surfaced, not silently dropped.\n\n"
            "https://github.com/timedrapery/friendly-meme",
        )

    def _show_cache_info(self) -> None:
        status = self._ctrl.status
        if not status.loaded:
            messagebox.showinfo(
                "Lexicon Not Loaded",
                "The lexicon has not been loaded yet.\n\n"
                "The app loads the lexicon automatically on startup.\n"
                "If it failed, check the status bar for the error message.",
            )
            return

        source = "cache" if status.from_cache else "network download (refreshed this session)"
        messagebox.showinfo(
            "Lexicon & Cache Information",
            f"Status      : loaded\n"
            f"Source      : {source}\n"
            f"Entries     : {status.entry_count}\n"
            f"Cache path  : {status.cache_path}\n\n"
            "The lexicon is cached locally so subsequent launches are fast\n"
            "and the app works offline.  Use Refresh Lexicon to force a\n"
            "fresh download from timedrapery/shiny-adventure on GitHub.",
        )
