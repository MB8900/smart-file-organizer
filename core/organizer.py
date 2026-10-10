"""
File organizer: builds operation plans and executes them with full UNDO support.
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import send2trash

# ---------------------------------------------------------------------------
# Category map  (extension → folder name)
# ---------------------------------------------------------------------------

CATEGORIES: dict[str, set[str]] = {
    "Immagini":   {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp",
                   ".tiff", ".tif", ".svg", ".heic", ".raw", ".cr2", ".nef", ".arw"},
    "Video":      {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv",
                   ".webm", ".m4v", ".3gp", ".ts", ".vob"},
    "Documenti":  {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt",
                   ".pptx", ".txt", ".odt", ".ods", ".odp", ".csv", ".rtf", ".md"},
    "Audio":      {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma",
                   ".m4a", ".opus", ".aiff"},
    "Archivi":    {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2",
                   ".xz", ".iso", ".cab"},
    "Eseguibili": {".exe", ".msi", ".bat", ".cmd", ".ps1", ".sh", ".appx", ".msix"},
    "Codice":     {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css",
                   ".java", ".cpp", ".c", ".h", ".go", ".rs", ".rb", ".php",
                   ".swift", ".kt", ".cs", ".json", ".yaml", ".yml", ".toml"},
    "Font":       {".ttf", ".otf", ".woff", ".woff2"},
}


@dataclass
class PlannedOperation:
    source: Path
    destination: Path
    operation: str = "move"   # "move" | "trash" | "delete"
    reason: str = ""


class Organizer:
    # A category (or a single year within it) stays flat below this many files,
    # instead of being split into Anno/Mese folders holding one file each.
    DATE_SPLIT_MIN = 20

    def __init__(self, undo_log: Path = Path("undo_history.json")) -> None:
        self.undo_log = undo_log

    # ------------------------------------------------------------------
    # Category resolution
    # ------------------------------------------------------------------

    def get_category(self, extension: str) -> str:
        ext = extension.lower()
        for cat, exts in CATEGORIES.items():
            if ext in exts:
                return cat
        return "Altro"   # same label the AI uses, so the two don't split

    # ------------------------------------------------------------------
    # Planning  (no filesystem changes)
    # ------------------------------------------------------------------

    def plan_organization(
        self,
        files: list,
        dest_root: Path,
        use_date_subfolders: bool = False,
        ai_suggestions: dict | None = None,
    ) -> list[PlannedOperation]:
        ops: list[PlannedOperation] = []
        ai = ai_suggestions or {}
        # Track destinations already claimed in this plan to avoid collisions
        claimed: set[Path] = set()

        # Pass 1 — resolve each file's category and count the buckets, so a
        # folder is only split by date when it actually holds enough files.
        resolved: list[tuple] = []
        per_category: dict[str, int] = {}
        per_year: dict[tuple[str, str], int] = {}

        for f in files:
            ai_data = ai.get(str(f.path), {})
            category = ai_data.get("category") or self.get_category(f.extension)
            year = f.modified.strftime("%Y")
            resolved.append((f, category, year, ai_data))
            per_category[category] = per_category.get(category, 0) + 1
            per_year[(category, year)] = per_year.get((category, year), 0) + 1

        # Pass 2 — build destinations, descending into Anno/Mese only as deep
        # as the file counts justify.
        for f, category, year, ai_data in resolved:
            dest_dir = dest_root / category
            if use_date_subfolders and per_category[category] >= self.DATE_SPLIT_MIN:
                dest_dir = dest_dir / year
                if per_year[(category, year)] >= self.DATE_SPLIT_MIN:
                    dest_dir = dest_dir / f.modified.strftime("%m")

            if ai_data.get("filename"):
                fname = ai_data["filename"] + f.extension
            else:
                fname = f.path.name

            dest = self._resolve_conflict(dest_dir / fname, claimed)
            claimed.add(dest)
            ops.append(PlannedOperation(source=f.path, destination=dest))

        return ops

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def execute(
        self,
        operations: list[PlannedOperation],
        dry_run: bool = False,
    ) -> list[dict]:
        log = self._load_log()
        executed: list[dict] = []

        for op in operations:
            if dry_run:
                executed.append({
                    "source": str(op.source),
                    "destination": str(op.destination),
                    "status": "dry_run",
                })
                continue

            entry: dict = {
                "source": str(op.source),
                "destination": str(op.destination),
                "timestamp": datetime.now().isoformat(),
            }
            try:
                if op.operation == "move":
                    op.destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(op.source), str(op.destination))
                    entry["status"] = "done"
                elif op.operation == "trash":
                    send2trash.send2trash(str(op.source))
                    entry["status"] = "trashed"
                elif op.operation == "delete":
                    op.source.unlink(missing_ok=True)
                    entry["status"] = "deleted"
                else:
                    entry["status"] = "skipped"
            except Exception as exc:
                entry["status"] = "error"
                entry["error"] = str(exc)

            executed.append(entry)

        if executed and not dry_run:
            log.append({"session": datetime.now().isoformat(), "operations": executed})
            self._save_log(log)

        return executed

    # ------------------------------------------------------------------
    # Undo
    # ------------------------------------------------------------------

    def undo_last_session(self) -> list[dict]:
        """Reverse all 'move' operations from the most recent session."""
        log = self._load_log()
        if not log:
            return []

        session = log.pop()
        results: list[dict] = []

        for op in reversed(session.get("operations", [])):
            if op.get("status") != "done":
                continue
            src = Path(op["destination"])
            dst = Path(op["source"])
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                results.append({"file": str(src), "status": "restored"})
            except Exception as exc:
                results.append({"file": str(src), "status": "error", "error": str(exc)})

        self._save_log(log)
        return results

    def get_history(self) -> list[dict]:
        return self._load_log()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def remove_empty_dirs(self, root: Path) -> list[str]:
        """
        Remove ONLY leaf directories that are already empty (no files AND no
        subdirectories) at the moment of the scan.  No cascade: a parent that
        becomes empty after we delete its children is NOT deleted in the same
        pass, so user-created organisational folders are never silently wiped.
        The root itself is never deleted.  Returns the list of removed paths.
        """
        # Snapshot: mark only truly leaf-empty dirs BEFORE deleting anything.
        # os.walk with topdown=False gives dirnames as they exist right now,
        # so a parent whose children appear in dirnames is NOT leaf-empty.
        to_delete: list[Path] = []
        for dirpath, dirnames, filenames in os.walk(root, topdown=False):
            p = Path(dirpath)
            if p == root:
                continue
            if not filenames and not dirnames:   # genuinely empty leaf
                to_delete.append(p)

        removed: list[str] = []
        for p in to_delete:
            try:
                send2trash.send2trash(str(p))
                removed.append(str(p))
            except Exception:
                pass
        return removed

    @staticmethod
    def _resolve_conflict(path: Path, claimed: set[Path] | None = None) -> Path:
        """Return *path* if free, otherwise append _1, _2, … until unique.
        *claimed* is an in-memory set of destinations already assigned in the
        current planning pass, so two files with the same AI filename don't
        both get the exact same destination even before any file is moved.
        """
        claimed = claimed or set()
        if not path.exists() and path not in claimed:
            return path
        stem, suffix, parent = path.stem, path.suffix, path.parent
        for n in range(1, 99_999):
            candidate = parent / f"{stem}_{n}{suffix}"
            if not candidate.exists() and candidate not in claimed:
                return candidate
        return path

    def _load_log(self) -> list:
        if self.undo_log.exists():
            try:
                return json.loads(self.undo_log.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return []
        return []

    def _save_log(self, log: list) -> None:
        self.undo_log.write_text(
            json.dumps(log, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
