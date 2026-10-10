# Contributing

Thanks for your interest. Changes are welcome: the license explicitly permits
you to modify the code and redistribute it, as long as the use stays
noncommercial.

## Before opening a pull request

Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), especially the **Safety
invariants** section. This program moves and deletes somebody else's files: a
bug here doesn't produce an error message, it produces an emptied documents
folder. The invariants exist because each one corresponds to something that
has already gone wrong.

The two that are easiest to violate without noticing:

- **Planning does not write.** `plan_organization()` and everything it calls
  must stay free of filesystem side effects.
- **Deletions do not cascade.** If your change can leave a folder empty and
  then remove it, re-read the section on removing empty directories.

## Development setup

```bash
git clone https://github.com/MB8900/smart-file-organizer.git
cd smart-file-organizer
py -3.12 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
py -3.12 main.py
```

AI classification is optional. To exercise it you need LM Studio listening on
port 1234 or Ollama on 11434; without either the app runs fine and falls back
to sorting by extension.

Note that the user interface and the folder names the program creates are in
Italian, while the code, comments and documentation are in English.

## Verifying a change to file-moving behaviour

There is no automated test suite, and a test against synthetic folders doesn't
catch the cases that matter. The method that found the real bugs is a
**planning-only pass over real data**:

```python
from core.organizer import Organizer
ops = Organizer().plan_organization(files, dest, use_date_subfolders=True)
for o in ops[:20]:
    print(o.source, "->", o.destination)
```

Because `core` has no dependency on the UI, this runs in a script of a few
lines. Check how many leaf folders the plan produces, how many hold a single
file, and whether any two destinations collide — **before** executing
anything.

If your change touches deletion, check which folders disappear too: count the
folders before and after, and don't take "the operation raised no error" as
evidence that it did the right thing.

CI runs [`check_plan_is_pure.py`](.github/scripts/check_plan_is_pure.py) on
every push, which asserts that planning performs no writes, that the
`DATE_SPLIT_MIN` threshold descends only where the file counts justify it, and
that no two operations share a destination. Extend it when you add behaviour
worth guarding.

## Style

- Python 3.11+, type annotations on public signatures.
- `from __future__ import annotations` at the top of every module.
- Comments explain the *why*, not the *what*. A comment that restates what the
  code already says should be deleted. One that records a non-obvious
  constraint or a past bug should be kept.
- No new dependency without a reason: there are six today, all permissively
  licensed.
- `core` does not import `ui`.
- `ruff check .` must pass; the configuration lives in `pyproject.toml`.

## Reporting a problem

Open an issue stating the version (Aiuto → Informazioni, the About dialog),
your operating system, what you asked the program to do and what it did
instead.

**Do not attach `undo_history.json`.** It contains the full paths of your own
files. If it's relevant, paste only the few lines that matter, after redacting
them.
