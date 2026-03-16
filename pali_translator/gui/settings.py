"""Persistent application settings for the Pāli translator workbench.

Settings are stored as JSON at ``~/.config/pali_translator/settings.json``.
Missing or corrupt files silently fall back to sane defaults so the app
always starts successfully even on a fresh machine.

Usage
-----
::

    settings = AppSettings.load()
    settings.font_size = 14
    settings.save()
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

# Default storage location — overridable in tests.
DEFAULT_SETTINGS_PATH = (
    Path.home() / ".config" / "pali_translator" / "settings.json"
)

_VALID_SORT_MODES = {"frequency", "alpha", "appearance"}


@dataclass
class AppSettings:
    """User-configurable workbench preferences.

    Attributes
    ----------
    font_size:
        Body font size for the output and inspector panes (8–24 pt).
    history_size:
        Maximum number of past sessions kept in the in-memory history (1–100).
    last_export_dir:
        Directory last used for an export, re-offered in the save dialog.
    concordance_sort:
        Default sort mode for the concordance panel.
        One of ``"frequency"``, ``"alpha"``, ``"appearance"``.
    auto_copy:
        When ``True``, automatically copy the translation to the clipboard
        after every successful translate operation.
    """

    font_size: int = 12
    history_size: int = 25
    last_export_dir: str = ""
    concordance_sort: str = "frequency"
    auto_copy: bool = False

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, path: Path | str | None = None) -> "AppSettings":
        """Load settings from *path* (defaults to :data:`DEFAULT_SETTINGS_PATH`).

        Returns default settings when the file is absent or contains invalid
        JSON.  Individual unknown keys in the file are silently ignored so
        older config files survive version upgrades.
        """
        target = Path(path) if path else DEFAULT_SETTINGS_PATH
        if not target.exists():
            return cls()
        try:
            raw = target.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            return cls()

        obj = cls()
        if isinstance(data.get("font_size"), int):
            obj.font_size = max(8, min(24, data["font_size"]))
        if isinstance(data.get("history_size"), int):
            obj.history_size = max(1, min(100, data["history_size"]))
        if isinstance(data.get("last_export_dir"), str):
            obj.last_export_dir = data["last_export_dir"]
        if data.get("concordance_sort") in _VALID_SORT_MODES:
            obj.concordance_sort = data["concordance_sort"]
        if isinstance(data.get("auto_copy"), bool):
            obj.auto_copy = data["auto_copy"]
        return obj

    def save(self, path: Path | str | None = None) -> None:
        """Write settings to *path* (defaults to :data:`DEFAULT_SETTINGS_PATH`).

        Creates parent directories as needed.  Silently does nothing on
        permission errors so a read-only environment doesn't crash the app.
        """
        target = Path(path) if path else DEFAULT_SETTINGS_PATH
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps(asdict(self), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass
