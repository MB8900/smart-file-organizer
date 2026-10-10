[English](README.md) · **Italiano**

# 📁 Smart File Organizer

> Riordina una cartella disordinata: raggruppa i file per tipo, riconosce i
> duplicati confrontandone il contenuto e usa un modello AI locale per capire
> di cosa parlano i tuoi documenti. Niente si muove senza che tu l'abbia visto
> prima, e ogni esecuzione è annullabile.

[![Python](https://img.shields.io/badge/Python-3.11+-3776ab?logo=python&logoColor=white)](https://www.python.org)
[![License](https://img.shields.io/badge/License-PolyForm%20Noncommercial%201.0.0-ad1457)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078d7?logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![GUI](https://img.shields.io/badge/GUI-CustomTkinter-1f6aa5)](https://github.com/TomSchimansky/CustomTkinter)
[![AI](https://img.shields.io/badge/AI-LM%20Studio%20%7C%20Ollama-ff6b35)](https://lmstudio.ai)
[![CI](https://github.com/MB8900/smart-file-organizer/actions/workflows/ci.yml/badge.svg)](https://github.com/MB8900/smart-file-organizer/actions/workflows/ci.yml)

---

## ⚖️ Licenza in breve

Questo programma è **gratuito e modificabile, ma non utilizzabile
commercialmente**.

| Puoi | Non puoi |
|------|----------|
| Usarlo per te, senza limiti di tempo | Venderlo, o venderne una versione modificata |
| Studiare e modificare il codice come vuoi | Usarlo nell'attività di un'azienda |
| Redistribuirlo, anche modificato | Offrirlo come servizio a pagamento |
| Usarlo in scuole, enti pubblici, ONLUS | Includerlo in un prodotto commerciale |

Licenza: **[PolyForm Noncommercial 1.0.0](LICENSE)**. Uso personale, studio,
ricerca, hobby, enti pubblici e organizzazioni non profit rientrano tutti negli
scopi permessi.

> **Nota per chi conosce l'argomento:** una licenza non commerciale non è
> "open source" secondo la definizione OSI, che non ammette restrizioni sul
> campo di impiego. GitHub la segnalerà come licenza non standard. Il codice è
> comunque leggibile, modificabile e redistribuibile: è *source available* con
> clausola non commerciale, che è esattamente l'intento.

---

## ✨ Cosa fa

| Funzione | Descrizione |
|----------|-------------|
| 🔍 **Scansione ricorsiva** | Thread separato, interrompibile anche a metà di un file da diversi GB |
| 🔑 **Duplicati per contenuto** | Impronta SHA-256 letta a blocchi: stesso contenuto byte per byte, nomi e date irrilevanti |
| 🗂️ **Smistamento per tipo** | 8 categorie — Immagini, Video, Documenti, Audio, Archivi, Eseguibili, Codice, Font |
| 📅 **Date adattive** | Sottocartelle Anno/Mese che scendono solo dove i file sono abbastanza da giustificarle |
| 🤖 **Classificazione AI** | LLM locale via LM Studio o Ollama: legge PDF/DOCX/TXT e propone categoria e nome file |
| 👁️ **Anteprima obbligatoria** | La tabella delle operazioni prima di ogni scrittura. Senza piano, il pulsante è spento |
| ↩️ **UNDO completo** | Ogni esecuzione è una sessione annullabile per intero |
| 🧭 **Guida al primo avvio** | Tour in 8 passi che pilota le schede mentre le spiega |
| 🎨 **Tema adattivo** | Chiaro / Scuro / Sistema |

### Privacy

Tutto resta sul tuo computer. Il modello AI gira in locale: nessun documento
viene inviato a servizi esterni, e il programma non effettua connessioni di
rete al di fuori di `localhost`.

---

## 🚀 Installazione

### Opzione A — eseguibile

Scarica `SmartFileOrganizer.exe` dalla pagina
[Releases](https://github.com/MB8900/smart-file-organizer/releases). Non
richiede Python.

### Opzione B — da sorgente

```bash
git clone https://github.com/MB8900/smart-file-organizer.git
cd smart-file-organizer
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

> Su Windows, se `python` risolve all'interprete sbagliato (capita quando altri
> programmi ne installano uno proprio), usa il launcher: `py -3.12 main.py`.
> `py -0p` elenca le versioni disponibili.

### Abilitare la classificazione AI (opzionale)

Serve uno dei due, in ascolto in locale:

| | Porta | Come |
|---|---|---|
| [LM Studio](https://lmstudio.ai) | 1234 | Carica un modello e avvia il server locale |
| [Ollama](https://ollama.com) | 11434 | `ollama pull llama3.2` |

L'app li rileva da sola all'avvio e il badge in alto diventa verde. Se nessuno
dei due è attivo, la funzione si disabilita e il programma lavora sulla
classificazione per estensione — nessun errore, nessun blocco.

Per documenti in italiano un modello da 7-8 miliardi di parametri è un buon
compromesso: circa 3 secondi per documento su una GPU di fascia media.

---

## 🖥️ Come si usa

Il flusso è sempre lo stesso, e le schede avanzano da sole:

```
Scansione  →  Risultati  →  Anteprima  →  Cronologia
 opzioni      statistiche   tabella       sessioni
 e avvio      e tabella     operazioni    e UNDO
```

1. **Scansione** — scegli la cartella sorgente e la destinazione (lasciandola
   vuota, riordina dentro la sorgente), spunta le opzioni, avvia.
2. **Risultati** — file trovati, duplicati, spazio occupato, categorie.
3. **Anteprima** — la tabella completa: sorgente, destinazione, operazione.
   Niente è ancora stato toccato. Se non ti convince, cambia le opzioni e
   rigenera quante volte vuoi.
4. **Esegui** — conferma. Ogni operazione viene registrata.
5. **Cronologia** — **Annulla Ultima Sessione** rimette tutto dov'era.

### Gestione duplicati

| Opzione | Comportamento | Reversibile |
|---------|---------------|-------------|
| Sposta in 'Duplicati' | Li raccoglie in una cartella dedicata | Sì, dall'app |
| Invia al Cestino | `send2trash` | Sì, dal Cestino di Windows |
| Elimina definitivamente | Rimozione immediata | **No** |

### Dove finiscono i dati dell'app

Cronologia UNDO e preferenze stanno in `%APPDATA%\SmartFileOrganizer`, non
accanto all'eseguibile. Ci arrivi da **Strumenti → Apri cartella dati**.

> `undo_history.json` contiene i percorsi completi dei tuoi file. È escluso dal
> versionamento e non va allegato a una segnalazione di problema.

---

## 📦 Build dell'eseguibile

```bat
build.bat
```

Oppure a mano:

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --collect-all customtkinter --icon=assets\icon.ico --name=SmartFileOrganizer main.py
```

Il risultato in `dist\SmartFileOrganizer.exe` è autonomo: nessun Python
necessario sul PC di destinazione.

> Aggiungi la tua icona in `assets\icon.ico` (256×256, ICO multi-risoluzione)
> prima della build, oppure togli l'opzione `--icon`.

---

## 📂 Struttura

```
smart-file-organizer/
├── main.py                       Entry point
├── version.py                    Nome, versione, autore, licenza
├── pyproject.toml                Metadati e configurazione ruff
├── requirements.txt
├── build.bat                     Build Windows → .exe
├── LICENSE                       PolyForm Noncommercial 1.0.0
├── CHANGELOG.md
├── CONTRIBUTING.md
├── docs/
│   └── ARCHITECTURE.md           Funzionamento tecnico del codice
├── core/                         Logica, nessuna dipendenza dall'interfaccia
│   ├── scanner.py                Attraversamento filesystem + SHA-256
│   ├── organizer.py              Categorie, pianificazione, esecuzione, UNDO
│   ├── ai_classifier.py          Classificazione via LLM locale
│   └── settings.py               Percorsi dati utente e preferenze
└── ui/
    ├── app.py                    Finestra principale e schede
    └── dialogs.py                Informazioni e tour guidato
```

---

## 🗂️ Categorie

| Categoria | Estensioni |
|-----------|-----------|
| Immagini | `.jpg` `.jpeg` `.png` `.gif` `.bmp` `.webp` `.tiff` `.heic` `.raw` `.svg` |
| Video | `.mp4` `.mkv` `.avi` `.mov` `.wmv` `.flv` `.webm` `.m4v` |
| Documenti | `.pdf` `.doc` `.docx` `.xls` `.xlsx` `.ppt` `.pptx` `.txt` `.csv` `.odt` |
| Audio | `.mp3` `.wav` `.flac` `.aac` `.ogg` `.wma` `.m4a` `.opus` |
| Archivi | `.zip` `.rar` `.7z` `.tar` `.gz` `.bz2` `.xz` `.iso` |
| Eseguibili | `.exe` `.msi` `.bat` `.cmd` `.ps1` `.appx` |
| Codice | `.py` `.js` `.ts` `.html` `.css` `.java` `.go` `.rs` `.cs` |
| Font | `.ttf` `.otf` `.woff` `.woff2` |
| Altro | tutto il resto |

Con la classificazione AI attiva, i documenti possono finire in categorie di
merito al posto del generico `Documenti`: Fatture, Contratti, Ricevute,
Rapporti, Manuali, Lettere, CV, Presentazioni, Ricerca, Moduli.

---

## 🔧 Come funziona, tecnicamente

[**docs/ARCHITECTURE.md**](docs/ARCHITECTURE.md) spiega il codice: struttura dei
moduli, modello di concorrenza, algoritmo di pianificazione in due passate,
rilevamento del backend AI, formato del log UNDO, e gli invarianti di sicurezza
da non violare in una modifica.

Vale la pena leggerlo prima di aprire una pull request: ogni invariante
corrisponde a qualcosa che è già andato storto una volta.

---

## 🤝 Contribuire

Le modifiche sono benvenute — la licenza ti autorizza esplicitamente a
modificare il codice. Leggi [CONTRIBUTING.md](CONTRIBUTING.md) (in inglese,
come il resto della documentazione tecnica) per l'impostazione dell'ambiente e
il metodo di verifica delle modifiche che toccano lo spostamento dei file.

---

## 📄 Licenza

[PolyForm Noncommercial 1.0.0](LICENSE) — Copyright © 2026 Marber (MB8900).

Libero per uso personale, studio, ricerca, hobby, enti pubblici e
organizzazioni non profit. L'uso commerciale non è concesso.

Dipendenze di terze parti, tutte con licenza permissiva: CustomTkinter (MIT),
Send2Trash (BSD-3), pypdf (BSD-3), python-docx (MIT), Pillow (MIT-CMU),
requests (Apache-2.0).
