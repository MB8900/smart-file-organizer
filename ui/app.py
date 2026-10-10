"""
Main CustomTkinter application — Smart File Organizer.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import tkinter as tk
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

import version
from core import settings as app_settings
from core.ai_classifier import AIClassifier
from core.organizer import Organizer
from core.scanner import Scanner
from ui.dialogs import AboutDialog, TourDialog


class App(ctk.CTk):
    _WIN_W, _WIN_H = 1100, 720
    _MIN_W, _MIN_H = 900, 580

    # Concurrent requests to the local LLM. One at a time leaves the GPU idle
    # between calls. Measured on LM Studio with a 7B model: 2.93 s/doc
    # sequential, 0.96 at 4 workers, 0.75 at 8, and no further gain at 12 —
    # the backend saturates around here.
    AI_WORKERS = 8

    # =================================================================
    # Init
    # =================================================================

    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.title(f"{version.APP_NAME}  {version.__version__}")
        self.geometry(f"{self._WIN_W}x{self._WIN_H}")
        self.minsize(self._MIN_W, self._MIN_H)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Core
        self.settings = app_settings.Settings()
        self.scanner = Scanner()
        self.organizer = Organizer(app_settings.undo_log_path())
        self.ai = AIClassifier()

        # State
        self.source_path: Path | None = None
        self.dest_path: Path | None = None
        self.scanned_files: list = []
        self.duplicates: dict = {}
        self.planned_ops: list = []
        self._plan_stop = threading.Event()

        self._setup_layout()
        self._update_ai_badge()

        if not self.settings.get("tour_seen"):
            self.after(400, self._show_tour)

    # =================================================================
    # Layout
    # =================================================================

    def _setup_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_menubar()
        self._build_header()
        self._build_tabs()

    def _build_menubar(self) -> None:
        bar = tk.Menu(self)

        m_file = tk.Menu(bar, tearoff=0)
        m_file.add_command(label="Seleziona cartella sorgente…",
                           command=self._pick_source)
        m_file.add_command(label="Seleziona cartella destinazione…",
                           command=self._pick_dest)
        m_file.add_separator()
        m_file.add_command(label="Esci", command=self._on_close)
        bar.add_cascade(label="File", menu=m_file)

        m_tools = tk.Menu(bar, tearoff=0)
        m_tools.add_command(label="Rileva di nuovo il backend AI",
                            command=self._redetect_ai)
        m_tools.add_command(label="Apri cartella dati dell'app",
                            command=self._open_data_dir)
        bar.add_cascade(label="Strumenti", menu=m_tools)

        m_help = tk.Menu(bar, tearoff=0)
        m_help.add_command(label="Guida introduttiva", command=self._show_tour)
        m_help.add_separator()
        m_help.add_command(
            label="Repository del progetto",
            command=lambda: webbrowser.open(version.REPO_URL),
        )
        m_help.add_command(
            label="Segnala un problema",
            command=lambda: webbrowser.open(f"{version.REPO_URL}/issues"),
        )
        m_help.add_separator()
        m_help.add_command(label=f"Informazioni su {version.APP_NAME}",
                           command=self._show_about)
        bar.add_cascade(label="Aiuto", menu=m_help)

        self.configure(menu=bar)

    def _build_header(self) -> None:
        bar = ctk.CTkFrame(self, height=52, corner_radius=0)
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            bar,
            text="📁  Smart File Organizer",
            font=ctk.CTkFont(size=17, weight="bold"),
        ).grid(row=0, column=0, padx=18, pady=10)

        self._ai_badge = ctk.CTkLabel(
            bar, text="", font=ctk.CTkFont(size=12)
        )
        self._ai_badge.grid(row=0, column=1, sticky="w", padx=8)

        self._theme_sw = ctk.CTkSwitch(
            bar,
            text="Tema scuro",
            onvalue="Dark",
            offvalue="Light",
            command=self._toggle_theme,
        )
        self._theme_sw.grid(row=0, column=2, padx=18)
        if ctk.get_appearance_mode() == "Dark":
            self._theme_sw.select()

    def _build_tabs(self) -> None:
        self._tabs = ctk.CTkTabview(self, corner_radius=8)
        self._tabs.grid(row=1, column=0, sticky="nsew", padx=12, pady=(6, 12))
        for tab in ("Scansione", "Risultati", "Anteprima", "Cronologia"):
            self._tabs.add(tab)

        self._build_scan_tab(self._tabs.tab("Scansione"))
        self._build_results_tab(self._tabs.tab("Risultati"))
        self._build_preview_tab(self._tabs.tab("Anteprima"))
        self._build_history_tab(self._tabs.tab("Cronologia"))

    # ---- Tab: Scansione ----

    def _build_scan_tab(self, tab: ctk.CTkFrame) -> None:
        tab.grid_columnconfigure(0, weight=1)

        self._source_entry = self._folder_row(
            tab, row=0, label="Cartella sorgente",
            cb=self._pick_source,
            placeholder="Seleziona la cartella da organizzare…",
        )
        self._dest_entry = self._folder_row(
            tab, row=1, label="Cartella destinazione",
            cb=self._pick_dest,
            placeholder="Lascia vuoto per usare la cartella sorgente",
        )

        # Options
        opts = ctk.CTkFrame(tab, corner_radius=8)
        opts.grid(row=2, column=0, sticky="ew", padx=4, pady=6)
        opts.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(
            opts, text="Opzioni",
            font=ctk.CTkFont(weight="bold"), anchor="w",
        ).grid(row=0, column=0, columnspan=3, padx=14, pady=(10, 4), sticky="w")

        self._opt_hash = ctk.CTkCheckBox(opts, text="Rileva duplicati  (SHA-256)")
        self._opt_hash.grid(row=1, column=0, padx=20, pady=(4, 10), sticky="w")
        self._opt_hash.select()

        self._opt_dates = ctk.CTkCheckBox(opts, text="Sottocartelle Anno / Mese")
        self._opt_dates.grid(row=1, column=1, padx=20, pady=(4, 10), sticky="w")

        self._opt_ai = ctk.CTkCheckBox(opts, text="Classificazione AI  (locale)")
        self._opt_ai.grid(row=1, column=2, padx=20, pady=(4, 10), sticky="w")

        self._opt_clean = ctk.CTkCheckBox(opts, text="Rimuovi cartelle vuote dopo esecuzione")
        self._opt_clean.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="w")
        self._opt_clean.select()

        # Duplicate handling
        dup = ctk.CTkFrame(tab, corner_radius=8)
        dup.grid(row=3, column=0, sticky="ew", padx=4, pady=6)
        dup.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(dup, text="Gestione duplicati:").grid(
            row=0, column=0, padx=14, pady=10
        )
        self._dup_combo = ctk.CTkComboBox(
            dup,
            values=[
                "Sposta in cartella 'Duplicati'",
                "Invia al Cestino",
                "Elimina definitivamente",
            ],
            width=250,
        )
        self._dup_combo.set("Sposta in cartella 'Duplicati'")
        self._dup_combo.grid(row=0, column=1, padx=14, pady=10, sticky="w")

        # Scan button
        self._scan_btn = ctk.CTkButton(
            tab,
            text="▶   Avvia Scansione",
            height=46,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._start_scan,
        )
        self._scan_btn.grid(row=4, column=0, sticky="ew", padx=4, pady=10)

        # Progress
        prog = ctk.CTkFrame(tab, corner_radius=8)
        prog.grid(row=5, column=0, sticky="ew", padx=4, pady=4)
        prog.grid_columnconfigure(0, weight=1)

        self._prog_bar = ctk.CTkProgressBar(prog)
        self._prog_bar.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 4))
        self._prog_bar.set(0)

        self._prog_lbl = ctk.CTkLabel(
            prog, text="In attesa…", text_color="gray"
        )
        self._prog_lbl.grid(row=1, column=0, padx=14, pady=(0, 12))

    # ---- Tab: Risultati ----

    def _build_results_tab(self, tab: ctk.CTkFrame) -> None:
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        stats = ctk.CTkFrame(tab, corner_radius=8)
        stats.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 6))
        stats.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self._lbl_total = self._stat_card(stats, "File trovati", "—", 0)
        self._lbl_dupes = self._stat_card(stats, "Duplicati", "—", 1)
        self._lbl_size  = self._stat_card(stats, "Dimensione tot.", "—", 2)
        self._lbl_cats  = self._stat_card(stats, "Categorie", "—", 3)

        self._res_tree = self._make_treeview(
            tab, row=1,
            cols=("name", "cat", "size", "modified", "flag"),
            heads=("Nome", "Categoria", "Dim.", "Modificato", "Note"),
            widths=(260, 110, 85, 140, 90),
        )

        self._plan_btn = ctk.CTkButton(
            tab,
            text="📋   Genera Piano Operazioni",
            height=42,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._start_plan,
            state="disabled",
        )
        self._plan_btn.grid(row=2, column=0, sticky="ew", padx=4, pady=10)

    # ---- Tab: Anteprima ----

    def _build_preview_tab(self, tab: ctk.CTkFrame) -> None:
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        info = ctk.CTkFrame(tab, corner_radius=8)
        info.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 6))
        self._preview_info = ctk.CTkLabel(
            info, text="Nessuna operazione pianificata.",
            font=ctk.CTkFont(size=13), anchor="w",
        )
        self._preview_info.grid(row=0, column=0, padx=14, pady=10, sticky="w")

        self._prev_tree = self._make_treeview(
            tab, row=1,
            cols=("src", "dst", "op"),
            heads=("Sorgente", "Destinazione", "Operazione"),
            widths=(310, 310, 110),
        )

        self._exec_btn = ctk.CTkButton(
            tab,
            text="✅   Esegui Operazioni",
            height=46,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2d7a2d",
            hover_color="#3a9c3a",
            command=self._execute_ops,
            state="disabled",
        )
        self._exec_btn.grid(row=2, column=0, sticky="ew", padx=4, pady=10)

    # ---- Tab: Cronologia ----

    def _build_history_tab(self, tab: ctk.CTkFrame) -> None:
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        self._hist_box = ctk.CTkTextbox(
            tab, font=ctk.CTkFont(family="Consolas", size=12), wrap="none"
        )
        self._hist_box.grid(row=0, column=0, sticky="nsew", padx=4, pady=(4, 6))

        self._undo_btn = ctk.CTkButton(
            tab,
            text="↩   Annulla Ultima Sessione",
            height=46,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#8b2020",
            hover_color="#b52929",
            command=self._undo_last,
        )
        self._undo_btn.grid(row=1, column=0, sticky="ew", padx=4, pady=10)

        self._refresh_history()

    # =================================================================
    # Widget helpers
    # =================================================================

    def _folder_row(
        self, parent: ctk.CTkFrame, row: int, label: str,
        cb, placeholder: str = "Seleziona cartella…",
    ) -> ctk.CTkEntry:
        frame = ctk.CTkFrame(parent, corner_radius=8)
        frame.grid(row=row, column=0, sticky="ew", padx=4, pady=4)
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text=label, width=190, anchor="w").grid(
            row=0, column=0, padx=14, pady=10
        )
        entry = ctk.CTkEntry(frame, placeholder_text=placeholder)
        entry.grid(row=0, column=1, sticky="ew", padx=6, pady=10)
        ctk.CTkButton(frame, text="Sfoglia…", width=90, command=cb).grid(
            row=0, column=2, padx=14, pady=10
        )
        return entry

    def _stat_card(
        self, parent: ctk.CTkFrame, label: str, value: str, col: int
    ) -> ctk.CTkLabel:
        card = ctk.CTkFrame(parent, corner_radius=8)
        card.grid(row=0, column=col, padx=5, pady=8, sticky="ew")
        ctk.CTkLabel(
            card, text=label, text_color="gray", font=ctk.CTkFont(size=11)
        ).pack(pady=(10, 0))
        val_lbl = ctk.CTkLabel(
            card, text=value, font=ctk.CTkFont(size=24, weight="bold")
        )
        val_lbl.pack(pady=(2, 10))
        return val_lbl

    def _make_treeview(
        self,
        parent: ctk.CTkFrame,
        row: int,
        cols: tuple,
        heads: tuple,
        widths: tuple,
    ) -> ttk.Treeview:
        frame = ctk.CTkFrame(parent, corner_radius=8)
        frame.grid(row=row, column=0, sticky="nsew", padx=4, pady=4)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        self._apply_treeview_style()

        tree = ttk.Treeview(
            frame, columns=cols, show="headings", style="App.Treeview"
        )
        for col, head, w in zip(cols, heads, widths, strict=True):
            tree.heading(col, text=head)
            tree.column(col, width=w, minwidth=50, stretch=True)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        return tree

    @staticmethod
    def _apply_treeview_style() -> None:
        mode = ctk.get_appearance_mode()
        bg = "#2b2b2b" if mode == "Dark" else "#f9f9f9"
        fg = "#e0e0e0" if mode == "Dark" else "#111111"

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "App.Treeview",
            background=bg, foreground=fg,
            fieldbackground=bg, rowheight=26,
            borderwidth=0, font=("Segoe UI", 10),
        )
        style.configure(
            "App.Treeview.Heading",
            background="#1a5276", foreground="white",
            font=("Segoe UI", 10, "bold"), relief="flat",
        )
        style.map("App.Treeview", background=[("selected", "#1f6aa5")])

    # =================================================================
    # Event handlers
    # =================================================================

    def _toggle_theme(self) -> None:
        ctk.set_appearance_mode(self._theme_sw.get())
        self._apply_treeview_style()

    def _update_ai_badge(self) -> None:
        if self.ai.available:
            backend = self.ai.backend.upper() if self.ai.backend else "AI"
            model   = self.ai.model or "modello locale"
            self._ai_badge.configure(
                text=f"● {backend} online  —  {model}", text_color="#3a9c3a"
            )
            self._opt_ai.configure(state="normal")
        else:
            self._ai_badge.configure(
                text="● AI offline  —  avvia LM Studio o Ollama per abilitarla",
                text_color="gray",
            )
            self._opt_ai.configure(state="disabled")
            self._opt_ai.deselect()

    # ---- Menu actions -----------------------------------------------

    def _ai_status_text(self) -> str:
        if not self.ai.available:
            return "non rilevato"
        backend = self.ai.backend.upper() if self.ai.backend else "AI"
        return f"{backend} — {self.ai.model or 'modello locale'}"

    def _show_about(self) -> None:
        AboutDialog(self, ai_status=self._ai_status_text())

    def _show_tour(self) -> None:
        TourDialog(self, settings=self.settings, on_tab=self._tabs.set)

    def _redetect_ai(self) -> None:
        self.ai.refresh_status()
        self._update_ai_badge()
        messagebox.showinfo("Backend AI", f"Stato: {self._ai_status_text()}")

    def _open_data_dir(self) -> None:
        d = app_settings.data_dir()
        if sys.platform == "win32":
            os.startfile(d)                              # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", str(d)], check=False)
        else:
            subprocess.run(["xdg-open", str(d)], check=False)

    def _pick_source(self) -> None:
        folder = filedialog.askdirectory(title="Seleziona cartella sorgente")
        if folder:
            self.source_path = Path(folder)
            self._source_entry.delete(0, "end")
            self._source_entry.insert(0, folder)

    def _pick_dest(self) -> None:
        folder = filedialog.askdirectory(title="Seleziona cartella destinazione")
        if folder:
            self.dest_path = Path(folder)
            self._dest_entry.delete(0, "end")
            self._dest_entry.insert(0, folder)

    # ---- Scan -------------------------------------------------------

    def _start_scan(self) -> None:
        if not self.source_path or not self.source_path.exists():
            messagebox.showerror("Errore", "Seleziona una cartella sorgente valida.")
            return

        self._scan_btn.configure(
            text="⏹   Interrompi", command=self._stop_scan
        )
        self._prog_bar.set(0)
        self._prog_lbl.configure(text="Avvio scansione…")
        self._plan_btn.configure(state="disabled")

        self.scanner.scan(
            self.source_path,
            progress_callback=self._on_progress,
            done_callback=self._on_scan_done,
            compute_hashes=bool(self._opt_hash.get()),
        )

    def _stop_scan(self) -> None:
        self.scanner.stop()
        self._scan_btn.configure(
            text="▶   Avvia Scansione", command=self._start_scan
        )
        self._prog_lbl.configure(text="Scansione interrotta.")

    def _on_progress(self, current: int, total: int) -> None:
        pct = current / total if total else 0
        self.after(0, self._prog_bar.set, pct)
        self.after(0, self._prog_lbl.configure,
                   {"text": f"Scansionati {current:,} / {total:,}  ({pct:.0%})"})

    def _on_scan_done(self, files: list) -> None:
        self.scanned_files = files
        self.duplicates = self.scanner.find_duplicates(files)

        dup_count   = sum(len(g) - 1 for g in self.duplicates.values())
        total_bytes = sum(f.size for f in files)
        cats        = len({self.organizer.get_category(f.extension) for f in files})
        dup_hashes  = set(self.duplicates)

        def ui_update() -> None:
            self._lbl_total.configure(text=f"{len(files):,}")
            self._lbl_dupes.configure(text=str(dup_count))
            self._lbl_size.configure(text=self._fmt_bytes(total_bytes))
            self._lbl_cats.configure(text=str(cats))

            for row in self._res_tree.get_children():
                self._res_tree.delete(row)
            for f in files[:10_000]:
                flag = "DUPLICATO" if f.sha256 in dup_hashes else ""
                self._res_tree.insert(
                    "", "end",
                    values=(
                        f.path.name,
                        self.organizer.get_category(f.extension),
                        self._fmt_bytes(f.size),
                        f.modified.strftime("%Y-%m-%d %H:%M"),
                        flag,
                    ),
                )

            self._scan_btn.configure(
                text="▶   Avvia Scansione", command=self._start_scan
            )
            self._prog_lbl.configure(
                text=f"Completato — {len(files):,} file trovati"
            )
            self._prog_bar.set(1.0)
            self._plan_btn.configure(state="normal")
            self._tabs.set("Risultati")

        self.after(0, ui_update)

    # ---- Plan (in background thread for AI) -------------------------

    def _start_plan(self) -> None:
        if not self.scanned_files:
            return

        self._plan_stop.clear()
        dest      = self.dest_path or self.source_path
        use_dates = bool(self._opt_dates.get())
        use_ai    = bool(self._opt_ai.get()) and self.ai.available

        if use_ai:
            self._plan_btn.configure(
                text="⏹   Interrompi classificazione AI", command=self._stop_plan
            )
        else:
            self._plan_btn.configure(state="disabled", text="Pianificazione in corso…")

        def worker() -> None:
            docs = [
                f for f in self.scanned_files
                if f.extension in AIClassifier.SUPPORTED_EXTENSIONS
            ] if use_ai else []

            ai_hints = self._classify_many(docs) if docs else {}

            ops = self.organizer.plan_organization(
                self.scanned_files, dest,
                use_date_subfolders=use_dates,
                ai_suggestions=ai_hints,
            )
            self.after(0, self._finalize_plan, ops)

        threading.Thread(target=worker, daemon=True).start()

    def _stop_plan(self) -> None:
        """Abandon the AI phase. The plan is still built, using whatever came
        back so far; the rest falls back to classification by extension."""
        self._plan_stop.set()
        self._plan_btn.configure(state="disabled", text="Interruzione…")

    def _classify_many(self, docs: list) -> dict:
        """Classify *docs*, keeping AI_WORKERS requests in flight at once."""
        hints: dict = {}
        total = len(docs)
        t0 = time.monotonic()

        pool = ThreadPoolExecutor(max_workers=self.AI_WORKERS)
        try:
            futures = {pool.submit(self.ai.classify, f.path): f for f in docs}
            for n, fut in enumerate(as_completed(futures), start=1):
                if self._plan_stop.is_set():
                    break
                try:
                    result = fut.result()
                except Exception:
                    result = None
                if result:
                    hints[str(futures[fut].path)] = result
                self._show_ai_progress(n, total, futures[fut].path.name, t0)
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

        m, s = divmod(int(time.monotonic() - t0), 60)
        verb = "interrotta" if self._plan_stop.is_set() else "completata"
        self.after(0, self._prog_bar.set, 1.0)
        self.after(0, self._prog_lbl.configure,
                   {"text": f"AI {verb}: {len(hints)} documenti classificati "
                            f"in {m}m {s:02d}s"})
        return hints

    def _show_ai_progress(self, n: int, total: int, name: str, t0: float) -> None:
        eta = ""
        if n > 1:
            remaining = (time.monotonic() - t0) / n * (total - n)
            m, s = divmod(int(remaining), 60)
            h, m = divmod(m, 60)
            # Hours are spelled out: on a large folder the honest number is the
            # one that tells you to stop rather than watch the bar crawl.
            if h:
                eta = f"  —  restano ~{h}h {m:02d}m"
            elif m:
                eta = f"  —  restano ~{m}m {s:02d}s"
            else:
                eta = f"  —  restano ~{s}s"

        short = name if len(name) <= 35 else name[:32] + "…"
        self.after(0, self._prog_bar.set, n / total)
        self.after(0, self._prog_lbl.configure,
                   {"text": f"AI  {n}/{total}  •  {short}{eta}"})
        self.after(0, self._plan_btn.configure,
                   {"text": f"⏹   Interrompi  —  {n} / {total}{eta}"})

    def _finalize_plan(self, ops: list) -> None:
        # Apply duplicate handling
        dup_choice  = self._dup_combo.get()
        dup_hashes  = set(self.duplicates)
        dup_by_path = {f.path: f.sha256 for f in self.scanned_files}
        dest        = self.dest_path or self.source_path

        for op in ops:
            if dup_by_path.get(op.source, "") in dup_hashes:
                if "Cestino" in dup_choice:
                    op.operation = "trash"
                elif "definitivamente" in dup_choice:
                    op.operation = "delete"
                else:
                    op.destination = dest / "Duplicati" / op.source.name

        self.planned_ops = ops

        for row in self._prev_tree.get_children():
            self._prev_tree.delete(row)
        for op in ops:
            self._prev_tree.insert(
                "", "end",
                values=(str(op.source), str(op.destination), op.operation),
            )

        n = len(ops)
        self._preview_info.configure(text=f"{n:,} operazioni pianificate")
        self._exec_btn.configure(
            state="normal",
            text=f"✅   Esegui {n:,} operazioni",
        )
        self._plan_btn.configure(
            state="normal", text="📋   Genera Piano Operazioni",
            command=self._start_plan,          # was rebound to _stop_plan
        )
        self._prog_lbl.configure(text=f"Piano generato: {n:,} operazioni")
        self._tabs.set("Anteprima")

    # ---- Execute ----------------------------------------------------

    def _execute_ops(self) -> None:
        n = len(self.planned_ops)
        if not messagebox.askyesno(
            "Conferma esecuzione",
            f"Stai per eseguire {n:,} operazioni.\n\n"
            "Le modifiche vengono registrate in undo_history.json\n"
            "e possono essere annullate dalla scheda Cronologia.\n\n"
            "Procedere?",
        ):
            return

        results = self.organizer.execute(self.planned_ops)
        done   = sum(1 for r in results if r.get("status") == "done")
        errors = sum(1 for r in results if r.get("status") == "error")

        # Remove empty directories if requested
        cleaned_msg = ""
        if bool(self._opt_clean.get()) and self.source_path:
            removed = self.organizer.remove_empty_dirs(self.source_path)
            if removed:
                cleaned_msg = f"\n🗑️  Cartelle vuote rimosse: {len(removed)}"

        messagebox.showinfo(
            "Operazioni completate",
            f"✅  Riuscite: {done:,}\n❌  Errori: {errors}"
            f"{cleaned_msg}\n\n"
            "Usa la scheda 'Cronologia' per annullare le modifiche.",
        )
        self.planned_ops.clear()
        self._exec_btn.configure(state="disabled", text="✅   Esegui Operazioni")
        self._preview_info.configure(text="Nessuna operazione pianificata.")
        self._refresh_history()
        self._tabs.set("Cronologia")

    # ---- Undo -------------------------------------------------------

    def _undo_last(self) -> None:
        log = self.organizer.get_history()
        if not log:
            messagebox.showinfo("Info", "Nessuna operazione da annullare.")
            return

        if not messagebox.askyesno(
            "Annulla sessione",
            "Riportare tutti i file dell'ultima sessione\n"
            "nelle posizioni originali?",
        ):
            return

        results = self.organizer.undo_last_session()
        restored = sum(1 for r in results if r.get("status") == "restored")
        errors   = sum(1 for r in results if r.get("status") == "error")
        messagebox.showinfo(
            "Undo completato",
            f"✅  Ripristinati: {restored:,}\n❌  Errori: {errors}",
        )
        self._refresh_history()

    def _refresh_history(self) -> None:
        log = self.organizer.get_history()
        self._hist_box.configure(state="normal")
        self._hist_box.delete("1.0", "end")

        if not log:
            self._hist_box.insert("end", "Nessuna cronologia disponibile.")
        else:
            for session in reversed(log):
                ops  = session.get("operations", [])
                done = [o for o in ops if o.get("status") == "done"]
                self._hist_box.insert(
                    "end",
                    f"{'─' * 64}\n"
                    f"Sessione: {session['session']}\n"
                    f"Operazioni completate: {len(done)}\n\n",
                )
                for op in done[:30]:
                    self._hist_box.insert(
                        "end",
                        f"  {Path(op['source']).name}\n"
                        f"    → {op['destination']}\n",
                    )
                if len(done) > 30:
                    self._hist_box.insert(
                        "end", f"  … e altri {len(done) - 30} file\n"
                    )
                self._hist_box.insert("end", "\n")

        self._hist_box.configure(state="disabled")

    # =================================================================
    # Utilities
    # =================================================================

    @staticmethod
    def _fmt_bytes(n: int) -> str:
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if n < 1024:
                return f"{n:.1f} {unit}"
            n //= 1024
        return f"{n} PB"

    def _on_close(self) -> None:
        self.scanner.stop()
        self.destroy()
