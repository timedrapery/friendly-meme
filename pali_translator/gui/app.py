"""Main Tkinter application window for the Pāli Translator Workbench.

Layout (left-to-right, top-to-bottom)
--------------------------------------
┌──────────────────────────────────────────────────────────────────────┐
│  Menu bar: File | Edit | Help                                        │
├──────────────────────┬───────────────────────────────────────────────┤
│  LEFT PANE           │  RIGHT PANE                                   │
│  ─ Source (Pāli)     │  ─ Translation output   [Copy Output]         │
│  ─ [Translate]       │  ─ Token Analysis table (scrollable)          │
│    [Clear]           │                                                │
│    [Refresh Lexicon] │                                                │
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
from .export import export_json, export_plain_text
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
)

_APP_TITLE   = "Pāli Translator Workbench"
_WINDOW_SIZE = "1280x800"
_MIN_W, _MIN_H = 900, 600

# Placeholder text shown in the source input when it is empty
_INPUT_HINT = "Enter a Pāli passage here…  (Ctrl+Return to translate)"


class App(tk.Tk):
    """Root window of the Pāli Translator Workbench application."""

    def __init__(self) -> None:
        super().__init__()
        self.title(_APP_TITLE)
        self.geometry(_WINDOW_SIZE)
        self.minsize(_MIN_W, _MIN_H)
        self.configure(bg=PAL_BG)

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
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.quit, accelerator="Ctrl+Q")
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

        # Token analysis header
        tok_header = tk.Frame(right, bg=PAL_BG)
        tok_header.pack(fill="x", padx=6, pady=(0, 2))
        tk.Label(
            tok_header, text="Token Analysis", font=FONT_LABEL, bg=PAL_BG, fg=PAL_FG, anchor="w",
        ).pack(side="left")
        self._unknown_label = tk.Label(
            tok_header, text="", font=FONT_SMALL, bg=PAL_BG, fg="#B5351A", anchor="e",
        )
        self._unknown_label.pack(side="right", fill="x", expand=True)

        # Token table (expands to fill remaining vertical space)
        self._token_table = TokenTable(right)
        self._token_table.pack(fill="both", expand=True, padx=6, pady=(0, 6))
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
            self._token_table.populate(session.token_rows)

        # Unknown-token summary
        n_unknown = len(result.unknown_tokens)
        if n_unknown:
            self._unknown_label.config(
                text=f"{n_unknown} unknown token{'s' if n_unknown != 1 else ''}  ·  shown in red below"
            )
        else:
            self._unknown_label.config(text="")

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
            title="Export Translation Report",
        )
        if not path:
            return

        try:
            content = export_plain_text(session)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
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
            title="Export Translation JSON",
        )
        if not path:
            return

        try:
            content = export_json(session)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
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
