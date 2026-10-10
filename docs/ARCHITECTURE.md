# Architettura

Documento tecnico: come è costruito il programma lato codice. Per l'uso
quotidiano vedi il [README](../README.md).

---

## 1. Principi

Tre vincoli hanno guidato il progetto, e spiegano quasi ogni scelta che segue.

**Niente modifiche non annunciate.** Pianificazione ed esecuzione sono due fasi
separate. `plan_organization()` non tocca il disco: produce una lista di
intenzioni che l'utente vede in tabella. Solo `execute()` scrive.

**Ogni scrittura è reversibile.** Ogni esecuzione produce una sessione nel log
UNDO con posizione di partenza e di arrivo di ogni file. Le cancellazioni di
cartelle passano dal Cestino, non da `rmdir()`.

**L'interfaccia non si blocca mai.** Scansione e classificazione AI girano in
thread separati; l'unico modo in cui toccano i widget è `self.after()`.

---

## 2. Struttura dei moduli

```
main.py                 entry point: costruisce App e avvia il mainloop
version.py              identità dell'app: nome, versione, autore, licenza

core/                   logica, nessuna dipendenza dall'interfaccia
  scanner.py            attraversamento del filesystem + SHA-256
  organizer.py          categorie, pianificazione, esecuzione, UNDO
  ai_classifier.py      classificazione documenti via LLM locale
  settings.py           percorsi dati per utente e preferenze

ui/
  app.py                finestra principale, schede, cablaggio eventi
  dialogs.py            finestra Informazioni e tour guidato
```

**La regola di dipendenza è unidirezionale:** `ui` importa `core`, `core` non
importa mai `ui`. Nessun modulo in `core` conosce CustomTkinter, apre finestre
di dialogo o stampa messaggi. Comunica solo tramite valori di ritorno e
callback. Questo è ciò che rende i moduli `core` utilizzabili da script — la
passata di migrazione del riordino è stata scritta esattamente così.

---

## 3. Modello di concorrenza

Tkinter non è thread-safe: i widget possono essere toccati solo dal thread che
ha creato la finestra. Il programma usa un unico schema per rispettarlo.

```
         thread principale (Tk)                thread worker (daemon)
         ─────────────────────                 ──────────────────────
         _start_scan()  ──────── avvia ──────▶ Scanner._worker()
                                                     │
                                                     │ per ogni file
         _on_progress()  ◀─── progress_cb ────────────┤
              │                                      │
              └─ self.after(0, widget.configure)      │
                                                      │
         _on_scan_done()  ◀──── done_cb ──────────────┘
              │
              └─ self.after(0, ui_update)
```

I callback `progress_cb` e `done_cb` vengono invocati **dal thread worker**. Non
toccano direttamente i widget: accodano il lavoro sul thread Tk con
`self.after(0, ...)`, che è l'unica chiamata Tkinter sicura da fuori. Lo stesso
schema regge la fase AI in `_start_plan()`, dove il worker aggiorna barra,
etichetta e testo del pulsante a ogni documento.

L'interruzione usa un `threading.Event`. `Scanner.stop()` lo imposta; il worker
lo controlla a ogni file *e a ogni blocco letto* dentro `_hash_file()`, così un
file da 4 GB non rende l'app insensibile al comando di stop.

I thread sono `daemon=True`: alla chiusura della finestra non trattengono il
processo.

---

## 4. `core/scanner.py`

### `FileInfo`

Dataclass con `path`, `size`, `extension`, `created`, `modified`, `sha256`.
Definisce `__hash__` e `__eq__` sul solo `path`, così i `FileInfo` si possono
mettere in insiemi e usare come chiavi di dizionario: due oggetti che
descrivono lo stesso percorso sono lo stesso file.

### Attraversamento

`_worker()` raccoglie prima **tutti** i percorsi con `os.walk()`, poi li
elabora. Due passaggi anziché uno, perché il totale serve per la percentuale di
avanzamento: senza conoscere il denominatore non si può mostrare una barra
sensata.

### Hashing

`_hash_file()` legge a blocchi di 65 536 byte con l'operatore walrus:

```python
while buf := fh.read(chunk):
    if self._stop.is_set():
        return ""
    h.update(buf)
```

Il file non viene mai caricato interamente in memoria, quindi un ISO da 8 GB
costa quanto un documento di testo in RAM. Un hash abbandonato restituisce la
stringa vuota, e `find_duplicates()` ignora gli hash vuoti: un confronto
interrotto non può produrre un falso duplicato.

Errori di permessi e di I/O vengono assorbiti in `_collect()` e `_hash_file()`
restituendo `None` o `""`. Una cartella di sistema illeggibile non interrompe
la scansione di tutte le altre.

### Rilevamento duplicati

`find_duplicates()` raggruppa per hash e tiene solo i gruppi con più di un
elemento. Il criterio è l'identità byte per byte: nomi, date e percorsi non
contano. Niente euristiche sui nomi simili, quindi nessun falso positivo.

---

## 5. `core/organizer.py`

Il cuore del programma.

### Categorie

`CATEGORIES` mappa un nome di cartella a un insieme di estensioni (8 categorie,
da `Immagini` a `Font`). `get_category()` restituisce la prima corrispondenza,
oppure `"Altro"` come ripiego.

> Il ripiego si chiama `"Altro"` e non `"Altri"` per una ragione precisa: è la
> stessa etichetta che l'AI può restituire. Nomi diversi producevano due
> cartelle per lo stesso concetto.

### Pianificazione in due passate

`plan_organization()` è deliberatamente in due passate, perché la profondità
della destinazione dipende da **quanti** file finiscono in ciascun gruppo —
informazione che non esiste finché non sono stati visti tutti.

**Passata 1** risolve la categoria di ogni file (suggerimento AI se presente,
altrimenti estensione) e conta i gruppi: `per_category` e `per_year`.

**Passata 2** costruisce le destinazioni scendendo solo quanto i conteggi
giustificano:

```
categoria con  < DATE_SPLIT_MIN file   →  Categoria/file
categoria con >= DATE_SPLIT_MIN file   →  Categoria/Anno/file
  e quell'anno >= DATE_SPLIT_MIN file  →  Categoria/Anno/Mese/file
```

`DATE_SPLIT_MIN` è 20. Senza questa soglia la suddivisione per data si
comportava in modo patologico sulle categorie piccole: tre curriculum
generavano sei cartelle su tre livelli, una per file. Su una cartella Download
reale, la soglia ha portato le cartelle foglia da 232 a 131 e quelle con un
solo file dentro da 104 a 36.

La data usata è `modified`, cioè in pratica la data di download — **non** la
data del documento. Una fattura del 2019 scaricata nel 2024 finisce sotto
`2024`. È una limitazione nota, non un difetto di implementazione: ricavare la
data di emissione richiederebbe di interpretare il contenuto.

### Collisioni di destinazione

`_resolve_conflict()` aggiunge `_1`, `_2`, … finché il percorso è libero,
controllando **due** cose:

```python
if not path.exists() and path not in claimed:
    return path
```

`claimed` è l'insieme delle destinazioni già assegnate nella pianificazione
corrente. Serve perché in fase di piano nessun file è ancora stato spostato:
due documenti a cui l'AI assegna lo stesso nome avrebbero entrambi passato il
controllo `exists()` e sarebbero finiti sullo stesso percorso, con il secondo
che sovrascrive il primo.

### Esecuzione

`execute()` scorre le operazioni e per ciascuna registra una voce con `source`,
`destination`, `timestamp` e `status`. Tre operazioni possibili:

| `operation` | effetto                     | `status` finale |
|-------------|-----------------------------|-----------------|
| `move`      | `shutil.move` + `mkdir -p`  | `done`          |
| `trash`     | `send2trash`                | `trashed`       |
| `delete`    | `Path.unlink`               | `deleted`       |

Ogni operazione è avvolta in un `try/except` che registra `status: "error"` con
il messaggio: un singolo file bloccato da un altro processo non interrompe le
restanti. Con `dry_run=True` non scrive né sul disco né sul log.

Il log viene scritto una volta sola, alla fine, come **una** sessione.

### UNDO

`undo_last_session()` estrae l'ultima sessione dal log e ripercorre le sue
operazioni **in ordine inverso**, invertendo solo quelle con
`status == "done"`. L'ordine inverso conta: ricrea le cartelle intermedie nello
stesso ordine in cui erano state consumate.

Solo gli spostamenti sono reversibili. Un `trash` è recuperabile dal Cestino di
Windows ma non dall'app, e un `delete` non è recuperabile — per questo
l'interfaccia propone il Cestino come impostazione predefinita.

### Rimozione cartelle vuote

Questa funzione ha avuto un difetto grave, e la forma attuale è una risposta
diretta a quel difetto.

L'implementazione iniziale percorreva l'albero con `os.walk(topdown=False)`
tentando `rmdir()` su ogni cartella. `rmdir()` da solo è sicuro — fallisce se
la cartella non è vuota — ma la combinazione produceva una **cascata**:
cancellate le foglie vuote, i genitori diventavano vuoti e sparivano anche
loro, poi i loro genitori. Su una cartella Download reale ha eliminato 232
cartelle, comprese quelle che l'utente considerava struttura e non vuoto.

La forma attuale separa osservazione e azione:

```python
to_delete = [p for p in walk(root)
             if not filenames and not dirnames]   # istantanea
for p in to_delete:
    send2trash(p)                                  # nessuna cascata
```

Lo scatto dell'istantanea avviene **prima** di qualsiasi cancellazione, quindi
una cartella che contiene sottocartelle al momento dell'osservazione non entra
nella lista, e non ci entrerà nemmeno se diventasse vuota durante
l'esecuzione. La radice non viene mai toccata, e le cartelle rimosse finiscono
nel Cestino.

Il principio, in una frase: **dal punto di vista dell'utente una cartella che
contiene sottocartelle non è vuota**, anche se non contiene file.

---

## 6. `core/ai_classifier.py`

### Rilevamento del backend

`refresh_status()` sonda due endpoint noti nell'ordine:

| Backend   | Porta | Sonda          | Generazione             |
|-----------|-------|----------------|-------------------------|
| LM Studio | 1234  | `/v1/models`   | `/v1/chat/completions`  |
| Ollama    | 11434 | `/api/tags`    | `/api/generate`         |

La prima risposta `200` vince, e `_detect_model()` prende il primo modello
dall'elenco. Nessuna configurazione richiesta. I due backend hanno formati di
richiesta incompatibili, quindi `_call_api()` smista verso
`_call_openai_compat()` o `_call_ollama()`.

Il fallimento è silenzioso per scelta: ogni percorso di errore restituisce
`None` e il chiamante ricade sulla classificazione per estensione. L'AI è un
miglioramento opzionale, non una dipendenza.

### Estrazione del testo

Solo `.pdf`, `.docx`, `.doc`, `.txt`, `.md`. Con tetti precisi: 5 pagine per i
PDF, 100 paragrafi per i DOCX, 2 000 caratteri inviati al modello. Un manuale
da 400 pagine costa quanto una fattura di una pagina, e il tipo di documento si
riconosce dall'intestazione.

### Interpretazione della risposta

`_parse_json()` non si fida che il modello restituisca JSON puro: ritaglia dalla
prima `{` all'ultima `}` e prova a interpretare quello. I modelli locali
piccoli spesso incorniciano la risposta con testo di cortesia, e questo lo
assorbe senza fallire.

### Validazione della categoria

`_validate()` confronta la categoria restituita con `ALLOWED_CATEGORIES`,
ignorando le maiuscole, e la normalizza alla forma canonica. Se non corrisponde
a nulla, **rimuove la categoria e tiene il nome file**, così il file ricade
sulla mappa per estensione ma conserva il rinomino descrittivo.

Serve perché un modello non vincolato invia la deriva: su una cartella reale ha
prodotto `Regolamenti`, `Leggi e normative` e `Dichiarazioni` — categorie
plausibili, fuori dall'elenco, ciascuna in una cartella da un file. Il prompt
chiede le 11 categorie ammesse, ma un prompt è una richiesta, non un vincolo:
il controllo deve stare nel codice.

---

## 7. `core/settings.py`

`data_dir()` restituisce una cartella scrivibile per utente
(`%APPDATA%\SmartFileOrganizer` su Windows, equivalenti XDG e macOS altrove).

Il log UNDO vive lì, non accanto all'eseguibile, per due ragioni: un .exe in
Program Files non ha permesso di scrittura nella propria cartella, e due utenti
sullo stesso PC non devono condividere una cronologia che contiene i percorsi
dei loro file.

`undo_log_path()` include una migrazione una-tantum: se trova un log pre-1.0
accanto all'app o nella cartella corrente, lo sposta nella nuova posizione.
Senza questo, un aggiornamento abbandonerebbe la cronologia esistente e
l'utente perderebbe la possibilità di annullare l'ultima esecuzione.

`Settings` è un contenitore JSON piatto che non solleva mai eccezioni: file
mancante o corrotto ricade sui valori predefiniti, e un errore di scrittura
viene ignorato. Le preferenze sono una comodità, non un dato critico.

---

## 8. `ui/`

`app.py` costruisce una `ctk.CTk` con intestazione, barra dei menu nativa
(`tkinter.Menu`) e quattro schede che corrispondono al flusso di lavoro:

```
Scansione  →  Risultati  →  Anteprima  →  Cronologia
  opzioni     statistiche    tabella       sessioni
  e avvio     e tabella      operazioni    e UNDO
```

Le schede avanzano da sole: alla fine della scansione `_on_scan_done()` passa a
Risultati, `_finalize_plan()` passa ad Anteprima. Il pulsante di esecuzione
nasce disabilitato e si abilita solo quando esiste un piano — non c'è modo di
eseguire senza essere passati dall'anteprima.

Le tabelle sono `ttk.Treeview`, non widget CustomTkinter: CTk non offre una
tabella, e il Treeview gestisce migliaia di righe con lo scorrimento nativo.
`_apply_treeview_style()` lo ritinge a mano quando cambia il tema, perché un
widget ttk non segue il tema CTk.

La stima del tempo residuo della fase AI è una media mobile semplice:

```python
per_doc = elapsed / (i - 1)
remaining = per_doc * (total - i)
```

Calcolata dal secondo documento in poi, perché il primo include il caricamento
del modello e sarebbe una base fuorviante.

`dialogs.py` contiene `AboutDialog` e `TourDialog`. Il tour guida la finestra
principale: ogni passo dichiara una scheda, e passando avanti l'utente vede
l'elemento di cui sta leggendo. Parte una sola volta, regolato da `tour_seen`
nelle preferenze, e si riapre da **Aiuto → Guida introduttiva**.

---

## 9. Formato di `undo_history.json`

Una lista di sessioni, in ordine cronologico. L'ultima è in coda.

```json
[
  {
    "session": "2026-10-10T12:09:53.123456",
    "operations": [
      {
        "source": "C:\\...\\Downloads\\Fatture\\2024\\01\\fattura.pdf",
        "destination": "C:\\...\\Downloads\\Fatture\\2024\\fattura.pdf",
        "timestamp": "2026-10-10T12:09:53.200000",
        "status": "done"
      }
    ]
  }
]
```

`status` vale `done`, `trashed`, `deleted`, `skipped`, `error` o `dry_run`. Con
`error` è presente anche una chiave `error` con il messaggio.

> Il file contiene i percorsi reali dei file dell'utente. È escluso in
> `.gitignore` e non va mai allegato a una segnalazione di problema senza
> averlo prima ripulito.

---

## 10. Invarianti di sicurezza

Da non violare in una modifica futura.

1. `plan_organization()` non scrive sul filesystem. Nessuna eccezione.
2. Nessuna esecuzione senza un piano visibile all'utente.
3. Ogni `move` viene registrato prima che la sessione si chiuda, o non è
   annullabile.
4. La rimozione di cartelle non si propaga verso l'alto, e passa dal Cestino.
5. `core` non importa `ui`.
6. I widget si toccano solo dal thread Tk, via `self.after()`.
7. La risposta del modello è dato non fidato: va validata, non applicata.

---

## 11. Estendere il programma

**Aggiungere una categoria per estensione** — una voce in `CATEGORIES`
(`organizer.py`). Nient'altro: `get_category()` la trova da sé.

**Aggiungere una categoria AI** — va in `ALLOWED_CATEGORIES`
(`ai_classifier.py`) **e** nell'elenco dentro i due prompt. Se la aggiungi solo
al prompt, `_validate()` la scarta.

**Aggiungere un backend LLM** — una voce in `_BACKENDS` con la sua sonda, un
metodo `_call_<nome>()` e uno smistamento in `_call_api()`.

**Cambiare la soglia di suddivisione** — `Organizer.DATE_SPLIT_MIN`. Più bassa
produce alberi più profondi, più alta cartelle più piatte e popolose.

**Aggiungere un passo al tour** — un dizionario in `STEPS` (`dialogs.py`). I
pallini di avanzamento e la navigazione si adattano alla lunghezza
dell'elenco.

---

## 12. Limiti noti

- La data di organizzazione è quella di modifica del file, non del documento.
- La classificazione AI legge solo le prime pagine: un documento con
  intestazione atipica può essere assegnato male.
- La tabella dei risultati si ferma a 10 000 righe per non ingolfare il
  Treeview. La scansione e il piano coprono comunque tutti i file.
- Nessuna suite di test automatici. Le modifiche al comportamento di
  spostamento vanno verificate con una passata di sola pianificazione su dati
  reali prima di eseguire.
- Non c'è rilevamento di duplicati *simili*, solo identici. Due esportazioni
  della stessa foto con compressione diversa sono due file distinti.
