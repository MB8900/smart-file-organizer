"""
Modal dialogs: the About window and the first-run guided tour.
Kept out of app.py so the main window stays about wiring, not copy.
"""

from __future__ import annotations

import sys
import webbrowser

import customtkinter as ctk

import version


def _center_on(win: ctk.CTkToplevel, parent, w: int, h: int) -> None:
    parent.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - h) // 3
    win.geometry(f"{w}x{h}+{max(x, 0)}+{max(y, 0)}")


def _make_modal(win: ctk.CTkToplevel, parent) -> None:
    win.transient(parent)
    win.resizable(False, False)
    # grab_set only works once the window is actually mapped on screen
    win.after(80, lambda: win.grab_set() if win.winfo_exists() else None)


# ---------------------------------------------------------------------------
# About
# ---------------------------------------------------------------------------

class AboutDialog(ctk.CTkToplevel):
    _W, _H = 520, 560

    def __init__(self, parent, ai_status: str = "") -> None:
        super().__init__(parent)
        self.title(f"Informazioni su {version.APP_NAME}")
        _center_on(self, parent, self._W, self._H)
        _make_modal(self, parent)

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="📁", font=ctk.CTkFont(size=44)
        ).grid(row=0, column=0, pady=(22, 0))

        ctk.CTkLabel(
            self, text=version.APP_NAME,
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=1, column=0)

        ctk.CTkLabel(
            self,
            text=f"Versione {version.__version__}  ·  {version.RELEASE_DATE}",
            text_color="gray",
        ).grid(row=2, column=0, pady=(2, 16))

        box = ctk.CTkFrame(self, corner_radius=8)
        box.grid(row=3, column=0, sticky="ew", padx=20)
        box.grid_columnconfigure(1, weight=1)

        rows = [
            ("Autore", version.AUTHOR),
            ("Licenza", version.LICENSE_NAME),
            ("Python", f"{sys.version_info.major}.{sys.version_info.minor}"
                       f".{sys.version_info.micro}"),
            ("CustomTkinter", getattr(ctk, "__version__", "n/d")),
            ("Backend AI", ai_status or "non rilevato"),
        ]
        for i, (k, v) in enumerate(rows):
            ctk.CTkLabel(
                box, text=k, text_color="gray", anchor="w", width=110,
            ).grid(row=i, column=0, sticky="w", padx=(14, 6), pady=5)
            ctk.CTkLabel(box, text=v, anchor="w").grid(
                row=i, column=1, sticky="w", pady=5
            )

        lic = ctk.CTkFrame(self, corner_radius=8)
        lic.grid(row=4, column=0, sticky="ew", padx=20, pady=14)
        lic.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            lic, text=version.LICENSE_SUMMARY,
            wraplength=440, justify="left", anchor="w",
        ).grid(row=0, column=0, padx=14, pady=12, sticky="w")

        third = ", ".join(f"{name} ({lcs})" for name, lcs in version.THIRD_PARTY)
        ctk.CTkLabel(
            self, text=f"Costruito con: {third}",
            text_color="gray", font=ctk.CTkFont(size=11),
            wraplength=470, justify="center",
        ).grid(row=5, column=0, padx=20)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=6, column=0, pady=18)
        ctk.CTkButton(
            btns, text="Repository", width=130,
            command=lambda: webbrowser.open(version.REPO_URL),
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            btns, text="Testo licenza", width=130, fg_color="gray",
            command=lambda: webbrowser.open(version.LICENSE_URL),
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            btns, text="Chiudi", width=100, command=self.destroy
        ).pack(side="left", padx=6)


# ---------------------------------------------------------------------------
# Guided tour
# ---------------------------------------------------------------------------

STEPS: list[dict] = [
    {
        "icon": "📁",
        "tab": None,
        "title": "Benvenuto",
        "body":
            "Smart File Organizer riordina una cartella disordinata: raggruppa "
            "i file per tipo, riconosce i duplicati confrontandone il contenuto "
            "e può usare un modello AI locale per capire di cosa parlano i tuoi "
            "documenti.\n\n"
            "Due cose da sapere subito:\n\n"
            "•  Non sposta nulla finché non hai visto l'anteprima e confermato.\n"
            "•  Ogni esecuzione è annullabile per intero.\n\n"
            "Questa guida dura un minuto. Puoi riaprirla da Aiuto → Guida.",
    },
    {
        "icon": "1️⃣",
        "tab": "Scansione",
        "title": "Scegliere le cartelle",
        "body":
            "La cartella sorgente è quella da riordinare. La destinazione è "
            "dove nascerà la struttura ordinata: se la lasci vuota, i file "
            "vengono riorganizzati dentro la sorgente stessa.\n\n"
            "La scansione è ricorsiva e gira in un thread separato, così la "
            "finestra resta reattiva anche su decine di migliaia di file. "
            "Il pulsante diventa «Interrompi» mentre lavora.",
    },
    {
        "icon": "2️⃣",
        "tab": "Scansione",
        "title": "Duplicati, per contenuto",
        "body":
            "Con «Rileva duplicati» ogni file viene letto a blocchi e ridotto "
            "a un'impronta SHA-256. Due file risultano duplicati se l'impronta "
            "coincide: stesso contenuto byte per byte, anche con nomi e date "
            "diversi. Nessun falso positivo per somiglianza di nome.\n\n"
            "Puoi scegliere se raccoglierli in una cartella «Duplicati», "
            "mandarli nel Cestino o eliminarli. In caso di dubbio scegli il "
            "Cestino: è l'unica delle tre opzioni reversibile dal sistema.",
    },
    {
        "icon": "3️⃣",
        "tab": "Scansione",
        "title": "Sottocartelle per data",
        "body":
            "Questa opzione aggiunge una suddivisione Anno/Mese dentro ogni "
            "categoria, basata sulla data di modifica del file.\n\n"
            "La discesa è graduale e si adatta ai numeri: una categoria con "
            "pochi file resta piatta, una grande scende all'anno, e solo un "
            "anno davvero popoloso arriva al mese. Serve a evitare il caso in "
            "cui tre documenti producano sei cartelle su tre livelli.",
    },
    {
        "icon": "4️⃣",
        "tab": "Scansione",
        "title": "Classificazione AI (opzionale)",
        "body":
            "Se sul tuo PC gira LM Studio o Ollama, l'app li rileva da sola e "
            "il badge in alto diventa verde. Il modello legge le prime pagine "
            "di PDF, DOCX, TXT e MD e propone una categoria di merito — "
            "Fatture, Contratti, Manuali — più un nome file descrittivo.\n\n"
            "Tutto resta sul tuo computer: nessun documento viene inviato a "
            "servizi esterni. Se l'AI non è disponibile, l'app ricade sulla "
            "classificazione per estensione e funziona comunque.",
    },
    {
        "icon": "5️⃣",
        "tab": "Anteprima",
        "title": "L'anteprima è obbligatoria",
        "body":
            "Qui vedi la tabella completa: per ogni file, da dove parte, dove "
            "arriverebbe e con quale operazione. Niente è ancora stato "
            "toccato.\n\n"
            "È il momento di controllare. Se qualcosa non ti convince, torna "
            "indietro, cambia le opzioni e rigenera il piano: puoi rifarlo "
            "quante volte vuoi senza conseguenze.",
    },
    {
        "icon": "6️⃣",
        "tab": "Cronologia",
        "title": "La rete di sicurezza",
        "body":
            "Ogni esecuzione viene registrata come una sessione: file per "
            "file, posizione di partenza e di arrivo. «Annulla Ultima "
            "Sessione» ripercorre quell'elenco al contrario e rimette tutto "
            "dov'era.\n\n"
            "Le cartelle rimaste vuote finiscono nel Cestino, non cancellate: "
            "e vengono rimosse solo se erano davvero vuote, senza propagarsi "
            "alle cartelle superiori.",
    },
    {
        "icon": "✅",
        "tab": "Scansione",
        "title": "Tutto pronto",
        "body":
            "Il percorso è sempre lo stesso: Scansione → Risultati → "
            "Anteprima → Cronologia.\n\n"
            "Un consiglio per la prima volta: prova su una cartella piccola, "
            "guarda il risultato, e solo dopo lanciala su Download o "
            "Documenti.\n\n"
            "Buon riordino.",
    },
]


class TourDialog(ctk.CTkToplevel):
    _W, _H = 620, 520

    def __init__(self, parent, settings=None, on_tab=None) -> None:
        super().__init__(parent)
        self.title(f"Guida — {version.APP_NAME}")
        _center_on(self, parent, self._W, self._H)
        _make_modal(self, parent)
        self.protocol("WM_DELETE_WINDOW", self._finish)

        self._settings = settings
        self._on_tab = on_tab
        self._i = 0

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._icon = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=40))
        self._icon.grid(row=0, column=0, pady=(24, 2))

        self._title = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=20, weight="bold")
        )
        self._title.grid(row=1, column=0, pady=(0, 10))

        body_frame = ctk.CTkFrame(self, corner_radius=8)
        body_frame.grid(row=2, column=0, sticky="nsew", padx=24)
        body_frame.grid_columnconfigure(0, weight=1)
        body_frame.grid_rowconfigure(0, weight=1)

        self._body = ctk.CTkLabel(
            body_frame, text="", wraplength=520,
            justify="left", anchor="nw", font=ctk.CTkFont(size=13),
        )
        self._body.grid(row=0, column=0, sticky="nsew", padx=18, pady=16)

        self._dots = ctk.CTkLabel(self, text="", text_color="gray")
        self._dots.grid(row=3, column=0, pady=(12, 0))

        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=4, column=0, sticky="ew", padx=24, pady=16)
        nav.grid_columnconfigure(1, weight=1)

        self._back_btn = ctk.CTkButton(
            nav, text="‹  Indietro", width=110, fg_color="gray",
            command=self._back,
        )
        self._back_btn.grid(row=0, column=0)

        self._skip_btn = ctk.CTkButton(
            nav, text="Salta", width=90, fg_color="transparent",
            text_color="gray", hover=False, command=self._finish,
        )
        self._skip_btn.grid(row=0, column=1)

        self._next_btn = ctk.CTkButton(
            nav, text="Avanti  ›", width=110, command=self._next
        )
        self._next_btn.grid(row=0, column=2)

        self._render()

    # -- navigation ----------------------------------------------------

    def _render(self) -> None:
        step = STEPS[self._i]
        self._icon.configure(text=step["icon"])
        self._title.configure(text=step["title"])
        self._body.configure(text=step["body"])
        self._dots.configure(
            text="  ".join(
                "●" if i == self._i else "○" for i in range(len(STEPS))
            )
            + f"     {self._i + 1} / {len(STEPS)}"
        )
        self._back_btn.configure(state="normal" if self._i else "disabled")
        last = self._i == len(STEPS) - 1
        self._next_btn.configure(text="Inizia" if last else "Avanti  ›")
        self._skip_btn.grid_remove() if last else self._skip_btn.grid()

        # Drive the main window to the tab being described, so the user is
        # looking at the thing the text is talking about.
        if step["tab"] and self._on_tab:
            try:
                self._on_tab(step["tab"])
            except Exception:
                pass

    def _next(self) -> None:
        if self._i == len(STEPS) - 1:
            self._finish()
            return
        self._i += 1
        self._render()

    def _back(self) -> None:
        if self._i:
            self._i -= 1
            self._render()

    def _finish(self) -> None:
        if self._settings is not None:
            self._settings.set("tour_seen", True)
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()
