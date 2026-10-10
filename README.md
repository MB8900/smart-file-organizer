**English** · [Italiano](README.it.md)

# 📁 Smart File Organizer

> Tidies up a messy folder: groups files by type, spots duplicates by comparing
> their contents, and uses a local AI model to work out what your documents are
> actually about. Nothing moves until you've seen it first, and every run can
> be undone.

[![Python](https://img.shields.io/badge/Python-3.11+-3776ab?logo=python&logoColor=white)](https://www.python.org)
[![License](https://img.shields.io/badge/License-PolyForm%20Noncommercial%201.0.0-ad1457)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078d7?logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![GUI](https://img.shields.io/badge/GUI-CustomTkinter-1f6aa5)](https://github.com/TomSchimansky/CustomTkinter)
[![AI](https://img.shields.io/badge/AI-LM%20Studio%20%7C%20Ollama-ff6b35)](https://lmstudio.ai)
[![CI](https://github.com/MB8900/smart-file-organizer/actions/workflows/ci.yml/badge.svg)](https://github.com/MB8900/smart-file-organizer/actions/workflows/ci.yml)

> **Heads up:** the interface, the built-in guide and the folder names the app
> creates are in **Italian**. The code, this README and
> [the architecture docs](docs/ARCHITECTURE.md) are in English. Category names
> live in one dictionary in `core/organizer.py`, so translating them is a
> single-file change — see the Categories section below.

---

## ⚖️ License in short

This program is **free and modifiable, but not for commercial use**.

| You may | You may not |
|---------|-------------|
| Use it yourself, with no time limit | Sell it, or sell a modified version |
| Study and modify the code however you like | Use it in the course of a business |
| Redistribute it, modified or not | Offer it as a paid service |
| Use it in schools, public bodies, non-profits | Bundle it into a commercial product |

License: **[PolyForm Noncommercial 1.0.0](LICENSE)**. Personal use, study,
research, hobby projects, public institutions and non-profit organizations all
count as permitted purposes.

> **If you follow licensing closely:** a noncommercial license is not "open
> source" by the OSI definition, which disallows field-of-use restrictions.
> GitHub will flag it as a non-standard license. The code is still readable,
> modifiable and redistributable: it's *source available* with a noncommercial
> clause, which is exactly the intent.

---

## ✨ What it does

| Feature | Description |
|---------|-------------|
| 🔍 **Recursive scan** | Runs on its own thread, interruptible even partway through a multi-GB file |
| 🔑 **Duplicates by content** | SHA-256 fingerprint read in chunks: identical byte for byte, names and dates irrelevant |
| 🗂️ **Sorting by type** | 8 categories — images, video, documents, audio, archives, executables, code, fonts |
| 📅 **Adaptive date folders** | Year/Month subfolders that only go deeper where there are enough files to justify it |
| 🤖 **AI classification** | Local LLM via LM Studio or Ollama: reads PDF/DOCX/TXT and suggests a category and filename |
| 👁️ **Mandatory preview** | The table of operations before any write. With no plan, the button stays off |
| ↩️ **Full undo** | Every run is a session that can be reversed in its entirety |
| 🧭 **First-run walkthrough** | An 8-step tour that drives the tabs while it explains them |
| 🎨 **Adaptive theme** | Light / Dark / System |

### Privacy

Everything stays on your machine. The AI model runs locally: no document is
sent to an external service, and the program makes no network connections
outside `localhost`.

---

## 🚀 Installation

### Option A — executable

Download `SmartFileOrganizer.exe` from the
[Releases](https://github.com/MB8900/smart-file-organizer/releases) page. No
Python needed.

### Option B — from source

```bash
git clone https://github.com/MB8900/smart-file-organizer.git
cd smart-file-organizer
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

> On Windows, if `python` resolves to the wrong interpreter (it happens when
> other programs install one of their own), use the launcher:
> `py -3.12 main.py`. `py -0p` lists the versions available.

### Enabling AI classification (optional)

You need one of these listening locally:

| | Port | How |
|---|---|---|
| [LM Studio](https://lmstudio.ai) | 1234 | Load a model and start the local server |
| [Ollama](https://ollama.com) | 11434 | `ollama pull llama3.2` |

The app detects either one by itself at startup and the badge at the top turns
green. If neither is running, the feature disables itself and the program falls
back to sorting by extension — no error, nothing blocked.

A 7-8 billion parameter model is a good trade-off: roughly 3 seconds per
document on a mid-range GPU.

---

## 🖥️ How to use it

The flow is always the same, and the tabs advance on their own:

```
Scansione  →  Risultati  →  Anteprima  →  Cronologia
  (scan)      (results)     (preview)     (history)
 options      statistics    operations     sessions
 and start    and table     table          and undo
```

1. **Scan** — pick the source folder and the destination (leave it empty to
   reorganize inside the source), tick the options, start.
2. **Results** — files found, duplicates, space used, categories.
3. **Preview** — the full table: source, destination, operation. Nothing has
   been touched yet. If it doesn't convince you, change the options and
   regenerate as many times as you like.
4. **Execute** — confirm. Every operation is recorded.
5. **History** — **Annulla Ultima Sessione** (undo last session) puts
   everything back where it was.

### Duplicate handling

| Option | Behaviour | Reversible |
|--------|-----------|------------|
| Move to 'Duplicati' | Collects them in a dedicated folder | Yes, from the app |
| Send to Recycle Bin | `send2trash` | Yes, from the Windows Recycle Bin |
| Delete permanently | Removed immediately | **No** |

### Where the app keeps its data

The undo history and preferences live in `%APPDATA%\SmartFileOrganizer`, not
next to the executable. You can open it from **Strumenti → Apri cartella dati**
(Tools → Open data folder).

> `undo_history.json` contains the full paths of your files. It's excluded from
> version control and should never be attached to a bug report.

---

## 📦 Building the executable

```bat
build.bat
```

Or by hand:

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --collect-all customtkinter --icon=assets\icon.ico --name=SmartFileOrganizer main.py
```

The result in `dist\SmartFileOrganizer.exe` is self-contained: no Python needed
on the target machine.

> Add your own icon at `assets\icon.ico` (256×256, multi-resolution ICO) before
> building, or drop the `--icon` flag.
>
> PyInstaller embeds the build directory into the binary, so a locally built
> executable carries your own username in its path. Prefer the CI-built
> artifact when publishing.

---

## 📂 Layout

```
smart-file-organizer/
├── main.py                       Entry point
├── version.py                    Name, version, author, license
├── pyproject.toml                Metadata and ruff configuration
├── requirements.txt
├── build.bat                     Windows build → .exe
├── LICENSE                       PolyForm Noncommercial 1.0.0
├── CHANGELOG.md
├── CONTRIBUTING.md
├── docs/
│   └── ARCHITECTURE.md           How the code works, technically
├── core/                         Logic, no dependency on the UI
│   ├── scanner.py                Filesystem traversal + SHA-256
│   ├── organizer.py              Categories, planning, execution, undo
│   ├── ai_classifier.py          Classification via local LLM
│   └── settings.py               Per-user data paths and preferences
└── ui/
    ├── app.py                    Main window and tabs
    └── dialogs.py                About window and guided tour
```

---

## 🗂️ Categories

Folder names are the Italian ones the app creates. They're defined in the
`CATEGORIES` dictionary in `core/organizer.py` — rename the keys there and the
whole program follows, since `get_category()` reads from that one map.

| Folder | English | Extensions |
|--------|---------|-----------|
| Immagini | Images | `.jpg` `.jpeg` `.png` `.gif` `.bmp` `.webp` `.tiff` `.heic` `.raw` `.svg` |
| Video | Video | `.mp4` `.mkv` `.avi` `.mov` `.wmv` `.flv` `.webm` `.m4v` |
| Documenti | Documents | `.pdf` `.doc` `.docx` `.xls` `.xlsx` `.ppt` `.pptx` `.txt` `.csv` `.odt` |
| Audio | Audio | `.mp3` `.wav` `.flac` `.aac` `.ogg` `.wma` `.m4a` `.opus` |
| Archivi | Archives | `.zip` `.rar` `.7z` `.tar` `.gz` `.bz2` `.xz` `.iso` |
| Eseguibili | Executables | `.exe` `.msi` `.bat` `.cmd` `.ps1` `.appx` |
| Codice | Code | `.py` `.js` `.ts` `.html` `.css` `.java` `.go` `.rs` `.cs` |
| Font | Fonts | `.ttf` `.otf` `.woff` `.woff2` |
| Altro | Everything else | the rest |

With AI classification on, documents can land in a meaningful category instead
of the generic `Documenti`: Fatture (invoices), Contratti (contracts), Ricevute
(receipts), Rapporti (reports), Manuali (manuals), Lettere (letters), CV,
Presentazioni (presentations), Ricerca (research), Moduli (forms).

---

## 🔧 How it works, technically

[**docs/ARCHITECTURE.md**](docs/ARCHITECTURE.md) explains the code: module
layout, concurrency model, the two-pass planning algorithm, AI backend
detection, the undo log format, and the safety invariants a change must not
violate.

It's worth reading before opening a pull request: every invariant corresponds
to something that has already gone wrong once.

---

## 🤝 Contributing

Changes are welcome — the license explicitly permits modifying the code. See
[CONTRIBUTING.md](CONTRIBUTING.md) for the development setup and for how to
verify a change that touches file moving.

---

## 📄 License

[PolyForm Noncommercial 1.0.0](LICENSE) — Copyright © 2026 Marber (MB8900).

Free for personal use, study, research, hobby projects, public institutions and
non-profit organizations. Commercial use is not granted.

Third-party dependencies, all under permissive licenses: CustomTkinter (MIT),
Send2Trash (BSD-3), pypdf (BSD-3), python-docx (MIT), Pillow (MIT-CMU),
requests (Apache-2.0).
