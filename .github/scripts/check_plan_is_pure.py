"""
Regressione sull'invariante numero 1: la pianificazione non scrive sul disco.

Verifica anche che la soglia DATE_SPLIT_MIN scenda di livello come previsto e
che un piano non assegni mai la stessa destinazione a due file. Gira senza
display, quindi è eseguibile in CI.
"""

from __future__ import annotations

import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.organizer import Organizer  # noqa: E402
from core.scanner import FileInfo  # noqa: E402

BIG, SMALL = 25, 3          # sopra e sotto DATE_SPLIT_MIN (20)


def snapshot(root: Path) -> list[str]:
    return sorted(str(p.relative_to(root)) for p in root.rglob("*"))


def as_fileinfo(p: Path) -> FileInfo:
    st = p.stat()
    return FileInfo(
        path=p,
        size=st.st_size,
        extension=p.suffix.lower(),
        created=datetime.fromtimestamp(st.st_ctime),
        modified=datetime.fromtimestamp(st.st_mtime),
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        made: list[Path] = []
        for i in range(BIG):                     # -> Documenti
            p = root / f"doc_{i}.pdf"
            p.write_text("x", encoding="utf-8")
            made.append(p)
        for i in range(SMALL):                   # -> Audio
            p = root / f"song_{i}.mp3"
            p.write_text("x", encoding="utf-8")
            made.append(p)

        files = [as_fileinfo(p) for p in made]
        before = snapshot(root)

        org = Organizer(undo_log=root / "non_deve_comparire.json")
        ops = org.plan_organization(files, root, use_date_subfolders=True)

        # 1. nessuna scrittura
        after = snapshot(root)
        if before != after:
            added = set(after) - set(before)
            print(f"FALLITO: plan_organization ha modificato il disco: {added}")
            return 1
        if (root / "non_deve_comparire.json").exists():
            print("FALLITO: il log UNDO è stato creato in fase di piano")
            return 1

        # 2. un'operazione per file, nessuna destinazione condivisa
        if len(ops) != len(files):
            print(f"FALLITO: {len(ops)} operazioni per {len(files)} file")
            return 1
        dests = [o.destination for o in ops]
        if len(set(dests)) != len(dests):
            print("FALLITO: due operazioni puntano alla stessa destinazione")
            return 1

        # 3. la soglia scende solo dove i numeri la giustificano
        depth = {}
        for o in ops:
            rel = o.destination.relative_to(root)
            depth.setdefault(rel.parts[0], set()).add(len(rel.parts) - 1)

        if depth.get("Documenti") != {3}:
            print(f"FALLITO: {BIG} file in Documenti attesi a 3 livelli "
                  f"(Categoria/Anno/Mese), trovati {depth.get('Documenti')}")
            return 1
        if depth.get("Audio") != {1}:
            print(f"FALLITO: {SMALL} file in Audio attesi piatti a 1 livello, "
                  f"trovati {depth.get('Audio')}")
            return 1

        print(f"OK: {len(ops)} operazioni pianificate, 0 scritture, "
              f"Documenti a 3 livelli, Audio piatto")
        return 0


if __name__ == "__main__":
    sys.exit(main())
