# Changelog

This file follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
the project uses [semantic versioning](https://semver.org/).

## [Unreleased]

### Changed
- **AI classification now runs 8 requests at a time instead of one.** Measured
  on LM Studio with a 7B model: 2.93 s per document sequentially, 0.96 s at 4
  workers, 0.75 s at 8, with no further gain at 12 — the backend saturates
  around there. On a folder of 17,000 documents that is the difference between
  roughly 14 hours and 3.5. Sending one request and waiting left the GPU idle
  between calls.
- `max_tokens` lowered from 80 to 48. The answer is a single short JSON object
  of about 30 tokens, and generation dominates the per-document cost.

### Added
- **The AI phase can be interrupted.** It previously ran to completion with the
  button disabled, so on a large folder the only way out was killing the
  application. Stopping now keeps the classifications already returned and
  falls back to sorting by extension for the rest.
- The remaining-time estimate shows hours when there are hours left. On a large
  folder the honest number is the one that tells you to stop rather than watch
  the bar crawl.
- Releases now also ship a `--onedir` portable ZIP beside the single-file exe,
  and both the release notes and the README explain why Windows warns about the
  download — unsigned binary, no reputation yet, and a self-extracting
  single-file build that matches what malware droppers look like.

## [1.0.0] — 2026-10-10

First public release.

### Added
- Four-tab CustomTkinter interface: scan, results, preview, history.
- Recursive scan on a background thread, interruptible even partway through
  hashing a large file.
- Duplicate detection by SHA-256 fingerprint read in chunks, with three
  handling modes: dedicated folder, Recycle Bin, permanent deletion.
- Sorting into 8 categories by extension, plus `Altro` as the fallback.
- Optional AI classification through a local LLM, auto-detecting LM Studio
  (port 1234) and Ollama (port 11434).
- Mandatory preview: nothing is written to disk before confirmation.
- Session-based undo, reversing an entire run.
- Menu bar with File, Tools and Help.
- About dialog showing version, license, active AI backend and dependencies.
- An 8-step guided tour on first run that drives the tabs of the main window
  while explaining them; reopenable from Help → Guided tour.
- Technical documentation of the code in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
- Adaptive date subfolders: a category stays flat below 20 files, descends to
  the year above that threshold, and to the month only for populous years.

### Fixed
- **Cascading removal of empty folders.** `os.walk(topdown=False)` with
  `rmdir()` on every directory deleted the empty leaves, then the parents left
  empty, then their parents: 232 folders removed on a real directory,
  including ones the user considered structure. Genuinely empty leaves are now
  identified from a snapshot taken before any deletion, and nothing propagates
  upwards.
- **Folders deleted permanently.** Removal used `rmdir()`, which bypasses the
  Recycle Bin. It now uses `send2trash`.
- **Colliding destinations within one plan.** Two documents the AI gave the
  same name ended up with identical paths, because the conflict check only
  looked at disk and nothing had been moved yet at planning time. Added the
  `claimed` set of destinations already assigned.
- **Categories invented by the model.** `Regolamenti`, `Leggi e normative` and
  `Dichiarazioni` each created a folder holding one file. The model's answer is
  now validated against `ALLOWED_CATEGORIES` and normalised; if it doesn't
  match, the category is dropped and only the suggested filename is kept.
- **`Altri` and `Altro`.** The extension fallback and the AI label used
  different names, producing two folders for the same concept. Unified on
  `Altro`.
- **Undo log not writable.** The file was created next to the application,
  where an exe installed in Program Files has no write permission. It now
  lives in `%APPDATA%\SmartFileOrganizer`, migrating an existing log
  automatically.
- The AI option label mentioned only Ollama despite supporting LM Studio.

### License
- Moved from MIT to **PolyForm Noncommercial 1.0.0**. MIT permits commercial
  use, which contradicts the intent of the project.
