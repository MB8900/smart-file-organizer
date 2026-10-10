# Come contribuire

Grazie per l'interesse. Le modifiche sono benvenute: la licenza ti autorizza
esplicitamente a modificare il codice e a redistribuirlo, purché l'uso resti
non commerciale.

## Prima di aprire una pull request

Leggi [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), in particolare la sezione
**Invarianti di sicurezza**. Questo programma sposta e cancella i file di
qualcun altro: un difetto non produce un messaggio di errore, produce una
cartella di documenti svuotata. Gli invarianti esistono perché ognuno di essi
corrisponde a qualcosa che è già andato storto.

I due che vengono violati più facilmente senza accorgersene:

- **La pianificazione non scrive.** `plan_organization()` e tutto ciò che
  chiama devono restare privi di effetti sul filesystem.
- **Le cancellazioni non si propagano.** Se la tua modifica può rendere vuota
  una cartella e poi rimuoverla, rileggi la sezione sulla rimozione delle
  cartelle vuote.

## Ambiente di sviluppo

```bash
git clone https://github.com/MB8900/smart-file-organizer.git
cd smart-file-organizer
py -3.12 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
py -3.12 main.py
```

La classificazione AI è opzionale. Per provarla serve LM Studio in ascolto sulla
porta 1234 oppure Ollama sulla 11434; senza nessuno dei due l'app funziona e
ricade sulla classificazione per estensione.

## Verificare una modifica al comportamento di spostamento

Non esiste una suite di test automatici, e un test su cartelle finte non
cattura i casi che contano. Il metodo che ha trovato i difetti reali è una
**passata di sola pianificazione su dati veri**:

```python
from core.organizer import Organizer
ops = Organizer().plan_organization(files, dest, use_date_subfolders=True)
for o in ops[:20]:
    print(o.source, "->", o.destination)
```

Poiché `core` non dipende dall'interfaccia, questo gira in uno script di
qualche riga. Controlla il numero di cartelle foglia prodotte, quante
contengono un solo file e quante destinazioni collidono, **prima** di eseguire
qualunque cosa.

Se la modifica tocca la cancellazione, verifica anche quali cartelle
spariscono: conta le cartelle prima e dopo, non fidarti del fatto che
l'operazione non abbia dato errore.

## Stile

- Python 3.11+, annotazioni di tipo sulle firme pubbliche.
- `from __future__ import annotations` in testa a ogni modulo.
- I commenti spiegano il *perché*, non il *cosa*. Se un commento descrive quello
  che il codice già dice, va togliato. Se documenta un vincolo non ovvio o un
  difetto passato, va tenuto.
- Nessuna dipendenza nuova senza motivo: oggi sono sei, tutte con licenza
  permissiva.
- `core` non importa `ui`.

## Segnalare un problema

Apri una issue indicando versione (Aiuto → Informazioni), sistema operativo,
cosa hai chiesto al programma e cosa ha fatto invece.

**Non allegare `undo_history.json`.** Contiene i percorsi completi dei tuoi
file. Se serve, incolla solo le poche righe pertinenti dopo averle ripulite.
