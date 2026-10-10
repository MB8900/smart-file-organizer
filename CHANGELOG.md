# Changelog

Il formato segue [Keep a Changelog](https://keepachangelog.com/it/1.1.0/)
e il progetto adotta il [versionamento semantico](https://semver.org/lang/it/).

## [1.0.0] — 2026-10-10

Prima versione pubblica.

### Aggiunto
- Interfaccia CustomTkinter a quattro schede: Scansione, Risultati, Anteprima,
  Cronologia.
- Scansione ricorsiva in thread separato, interrompibile anche durante
  l'hashing di un file di grandi dimensioni.
- Rilevamento duplicati per impronta SHA-256 calcolata a blocchi, con tre
  modalità di gestione: cartella dedicata, Cestino, eliminazione.
- Smistamento in 8 categorie per estensione, più `Altro` come ripiego.
- Classificazione AI opzionale tramite LLM locale, con rilevamento automatico
  di LM Studio (porta 1234) e Ollama (porta 11434).
- Anteprima obbligatoria: nessuna scrittura sul disco prima della conferma.
- Sistema UNDO per sessioni, con annullamento completo dell'ultima esecuzione.
- Barra dei menu con File, Strumenti e Aiuto.
- Finestra Informazioni con versione, licenza, backend AI attivo e dipendenze.
- Tour guidato in 8 passi al primo avvio, che pilota le schede della finestra
  principale mentre spiega; riapribile da Aiuto → Guida introduttiva.
- Documentazione tecnica del codice in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
- Suddivisione per data adattiva: una categoria resta piatta sotto i 20 file,
  scende all'anno oltre quella soglia e al mese solo per gli anni popolosi.

### Corretto
- **Rimozione cartelle vuote a cascata.** `os.walk(topdown=False)` con `rmdir()`
  su ogni cartella eliminava le foglie vuote, poi i genitori rimasti vuoti, poi
  i loro genitori: 232 cartelle rimosse su una cartella reale, comprese quelle
  che l'utente considerava struttura. Ora le foglie realmente vuote vengono
  individuate con un'istantanea presa prima di qualsiasi cancellazione, e non
  c'è propagazione verso l'alto.
- **Cartelle eliminate definitivamente.** La rimozione usava `rmdir()`, che non
  passa dal Cestino. Ora usa `send2trash`.
- **Collisione di destinazioni nello stesso piano.** Due documenti a cui l'AI
  assegnava lo stesso nome ottenevano percorsi identici, perché il controllo di
  conflitto guardava solo il disco e in fase di piano nulla era ancora stato
  spostato. Aggiunto l'insieme `claimed` delle destinazioni già assegnate.
- **Categorie inventate dal modello.** `Regolamenti`, `Leggi e normative` e
  `Dichiarazioni` creavano cartelle da un file. La risposta del modello viene
  ora validata contro `ALLOWED_CATEGORIES` e normalizzata; se non corrisponde,
  la categoria viene scartata e si conserva il solo nome file suggerito.
- **`Altri` e `Altro`.** Il ripiego per estensione e l'etichetta dell'AI usavano
  nomi diversi, producendo due cartelle per lo stesso concetto. Unificati su
  `Altro`.
- **Log UNDO non scrivibile.** Il file veniva creato accanto all'applicazione,
  dove un .exe installato in Program Files non ha permesso di scrittura. Ora
  vive in `%APPDATA%\SmartFileOrganizer`, con migrazione automatica di un log
  preesistente.
- Etichetta dell'opzione AI che citava solo Ollama pur supportando LM Studio.

### Licenza
- Passaggio da MIT a **PolyForm Noncommercial 1.0.0**. MIT autorizzava l'uso
  commerciale, in contrasto con l'intento del progetto.
