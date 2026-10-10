"""
File scanner with SHA-256 hashing and duplicate detection.
Runs in a background thread to keep the UI responsive.
"""

from __future__ import annotations

import hashlib
import os
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class FileInfo:
    path: Path
    size: int
    extension: str
    created: datetime
    modified: datetime
    sha256: str = ""

    def __hash__(self) -> int:
        return hash(self.path)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FileInfo) and self.path == other.path


class Scanner:
    def __init__(self) -> None:
        self._stop = threading.Event()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan(
        self,
        folder: Path,
        progress_callback: Callable[[int, int], None] | None = None,
        done_callback: Callable[[list[FileInfo]], None] | None = None,
        compute_hashes: bool = True,
    ) -> threading.Thread:
        """Start scanning *folder* in a background daemon thread."""
        self._stop.clear()
        t = threading.Thread(
            target=self._worker,
            args=(folder, progress_callback, done_callback, compute_hashes),
            daemon=True,
        )
        t.start()
        return t

    def stop(self) -> None:
        """Signal the running scan to stop."""
        self._stop.set()

    def find_duplicates(self, files: list[FileInfo]) -> dict[str, list[FileInfo]]:
        """Return groups that share the same SHA-256 hash (duplicates only)."""
        buckets: dict[str, list[FileInfo]] = {}
        for f in files:
            if f.sha256:
                buckets.setdefault(f.sha256, []).append(f)
        return {h: g for h, g in buckets.items() if len(g) > 1}

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _worker(
        self,
        folder: Path,
        progress_cb: Callable | None,
        done_cb: Callable | None,
        compute_hashes: bool,
    ) -> None:
        all_paths: list[Path] = []
        for root, _, names in os.walk(folder):
            for name in names:
                all_paths.append(Path(root) / name)

        total = len(all_paths)
        results: list[FileInfo] = []

        for idx, path in enumerate(all_paths, start=1):
            if self._stop.is_set():
                break
            info = self._collect(path, compute_hashes)
            if info is not None:
                results.append(info)
            if progress_cb:
                progress_cb(idx, total)

        if done_cb:
            done_cb(results)

    def _collect(self, path: Path, compute_hashes: bool) -> FileInfo | None:
        try:
            st = path.stat()
            sha = self._hash_file(path) if compute_hashes else ""
            return FileInfo(
                path=path,
                size=st.st_size,
                extension=path.suffix.lower(),
                created=datetime.fromtimestamp(st.st_ctime),
                modified=datetime.fromtimestamp(st.st_mtime),
                sha256=sha,
            )
        except (PermissionError, OSError):
            return None

    def _hash_file(self, path: Path, chunk: int = 65_536) -> str:
        h = hashlib.sha256()
        try:
            with open(path, "rb") as fh:
                while buf := fh.read(chunk):
                    if self._stop.is_set():
                        return ""
                    h.update(buf)
        except (PermissionError, OSError):
            return ""
        return h.hexdigest()
