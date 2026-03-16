"""pali_translator.gui — Tkinter desktop app for the Pāli Translator Workbench.

Launch via
----------
::

    # Module entry point
    python -m pali_translator.gui

    # Console script (when installed)
    pali-translator-gui

Programmatic usage::

    from pali_translator.gui import App

    app = App()
    app.mainloop()
"""

from .app import App

__all__ = ["App"]
