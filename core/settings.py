"""
Per-user settings and data locations.

The app writes its UNDO log and settings under the user's profile, not next to
the executable: a PyInstaller build dropped in Program Files has no write
permission there, and two users on the same machine must not share a history.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

APP_DIR_NAME = "SmartFileOrganizer"
UNDO_FILENAME = "undo_history.json"
SETTINGS_FILENAME = "settings.json"


def data_dir() -> Path:
    """Writable per-user directory for this app, created on demand."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    d = base / APP_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def _app_dir() -> Path:
    """Directory the app runs from — the exe's folder when frozen."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def undo_log_path() -> Path:
    """
    Path of the UNDO log, migrating a pre-1.0 log that sat next to the app.
    Without this, upgrading would silently strand an existing history and the
    user would lose the ability to revert their last run.
    """
    target = data_dir() / UNDO_FILENAME
    if target.exists():
        return target
    for legacy in (_app_dir() / UNDO_FILENAME, Path.cwd() / UNDO_FILENAME):
        if legacy.is_file():
            try:
                shutil.move(str(legacy), str(target))
                return target
            except OSError:
                return legacy          # keep using it in place rather than fail
    return target


class Settings:
    """Flat JSON settings bag; never raises on a missing or corrupt file."""

    DEFAULTS: dict = {
        "tour_seen": False,
        "theme": "System",
    }

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (data_dir() / SETTINGS_FILENAME)
        self._data = dict(self.DEFAULTS)
        self.load()

    def load(self) -> None:
        try:
            stored = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if isinstance(stored, dict):
            self._data.update(stored)

    def save(self) -> None:
        try:
            self.path.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass                       # settings are a convenience, not critical

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        self._data[key] = value
        self.save()
