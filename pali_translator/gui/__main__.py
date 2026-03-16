"""Entry point for ``python -m pali_translator.gui``.

Provides a clear error message when Tkinter is not available in the current
Python installation instead of an unhelpful ImportError traceback.
"""

from __future__ import annotations


def main() -> None:
    """Launch the Pāli Translator Workbench desktop application."""
    try:
        import tkinter  # noqa: F401
    except ImportError:
        print(
            "The Pāli Translator GUI requires Tkinter, which is not available "
            "in this Python installation.\n\n"
            "  On Debian/Ubuntu : sudo apt-get install python3-tk\n"
            "  On macOS (pyenv) : install Python via the official macOS installer\n"
            "  On Windows       : Tkinter is bundled with the standard Python installer\n"
        )
        raise SystemExit(1)

    from .app import App

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
