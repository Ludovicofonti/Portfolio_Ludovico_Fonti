# Documentazione Tecnica — PDF to Markdown Converter

Web app locale per convertire PDF in Markdown pulito. RapidOCR/ONNX è il motore predefinito, veloce anche su CPU modeste; Ollama con GLM-OCR è disponibile come modalità opzionale. Il progetto è organizzato in un backend FastAPI e un frontend statico servito dallo stesso processo.

L'output Markdown è pensato anche per rendere i documenti più navigabili da strumenti come GitHub Copilot, Codex, Claude Code e altri agenti coding: una volta convertito, il contenuto può essere indicizzato dal workspace, cercato con strumenti testuali, citato nei prompt e modificato come normale documentazione versionabile.

---

## Architettura

```
frontend/
  index.html + CSS + JavaScript
        │
        ▼
FastAPI backend
        │
        ├── Upload e validazione PDF
        ├── Estrazione nativa del text layer con PyMuPDF
        ├── Rendering incrementale delle sole pagine scansionate
        ├── OCR locale pagina per pagina via RapidOCR o Ollama
        ├── Assemblaggio Markdown
        ├── Stato job in memoria
        └── Download .md / .zip
```

## Struttura del Progetto

```text
Script/
├── start.ps1                       # Avvio local-only su 127.0.0.1
├── .env.example                    # Riferimento per le variabili d'ambiente
├── examples/                       # PDF sintetici e relativo generatore
├── backend/
│   ├── app/
│   │   ├── main.py                 # Entry point FastAPI, static files, health check
│   │   ├── config.py               # Configurazione da variabili d'ambiente
│   │   ├── api/
│   │   │   ├── upload.py           # Upload singolo e batch
│   │   │   ├── status.py           # Stato, progress SSE, preview
│   │   │   └── download.py         # Download Markdown e ZIP batch
│   │   ├── models/
│   │   │   └── schemas.py          # Modelli Pydantic
│   │   └── services/
│   │       ├── job_manager.py      # Job store in memoria e pipeline conversione
│   │       ├── pdf_renderer.py     # PDF → immagini PNG base64
│   │       ├── ocr_service.py      # Selezione motore OCR locale
│   │       ├── ocr_client.py       # Client opzionale verso Ollama
│   │       └── markdown_assembler.py
│   ├── tests/
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── pyproject.toml
└── frontend/
    ├── index.html
    ├── css/style.css
    └── js/app.js
```

## Pipeline di Conversione

1. **Upload**
   - L'utente carica uno o più PDF tramite interfaccia web o client multipart.
   - Il backend verifica content type, magic bytes `%PDF-`, dimensione massima, protezione password e numero massimo di pagine.

2. **Creazione Job**
   - Ogni file genera un `ConversionJob` identificato da UUID.
   - Lo stato viene mantenuto in memoria tramite `JobManager`.

3. **Estrazione e rendering incrementale**
   - PyMuPDF estrae direttamente il testo dalle pagine che hanno un text layer valido.
   - Solo le pagine scansionate vengono renderizzate in PNG.
   - Viene mantenuta in RAM una sola immagine base64 alla volta.

4. **OCR**
   - Con `OCR_ENGINE=rapidocr`, i modelli ONNX inclusi elaborano l'immagine nello stesso processo Python.
   - Con `OCR_ENGINE=ollama`, `ocr_client.py` invia la pagina soltanto a un endpoint loopback tramite `POST /api/generate`.
   - Le pagine e i job vengono processati in modo sequenziale per limitare RAM e carico CPU.

5. **Assemblaggio Markdown**
   - `markdown_assembler.py` pulisce il testo OCR:
     - ricompone parole spezzate da trattino a fine riga
     - collassa righe vuote multiple
     - rimuove numeri pagina isolati
     - normalizza spazi prima della punteggiatura
   - Le pagine vengono unite con separatore Markdown `---`.

6. **Preview e Download**
   - Il frontend mostra una preview read-only.
   - L'utente può scaricare un `.md` per singolo file o uno `.zip` per batch.

## API

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| `GET` | `/` | Serve il frontend |
| `GET` | `/api/health` | Verifica disponibilità, località e privacy del motore OCR |
| `POST` | `/api/upload` | Carica un PDF e avvia una conversione |
| `POST` | `/api/upload/batch` | Carica più PDF e avvia job separati |
| `GET` | `/api/jobs/{job_id}/status` | Restituisce lo stato del job |
| `GET` | `/api/jobs/{job_id}/progress` | Stream SSE con avanzamento pagina per pagina |
| `GET` | `/api/jobs/{job_id}/preview` | Restituisce Markdown e warning |
| `GET` | `/api/jobs/{job_id}/download` | Scarica il risultato `.md` |
| `GET` | `/api/jobs/batch/download` | Scarica più risultati in formato `.zip` |
| `DELETE` | `/api/jobs/{job_id}` | Cancella job, PDF e risultato dalla memoria del processo |

## Configurazione

Le variabili d'ambiente sono opzionali. `.env.example` è un riferimento e non viene caricato automaticamente: impostare le variabili nella sessione PowerShell prima dell'avvio.

| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `OCR_ENGINE` | `rapidocr` | `rapidocr` per velocità CPU oppure `ollama` per GLM-OCR |
| `OLLAMA_MODEL` | `glm-ocr:q8_0` | Modello usato soltanto con `OCR_ENGINE=ollama` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Endpoint usato soltanto con Ollama; deve essere loopback in modalità privacy |
| `OLLAMA_KEEP_ALIVE` | `10m` | Permanenza del modello Ollama in RAM dopo una richiesta |
| `ALLOW_REMOTE_OCR` | `false` | Opt-in remoto per Ollama, da non usare con dati riservati |
| `MAX_FILE_SIZE_MB` | `25` | Dimensione massima per file |
| `MAX_BATCH_FILES` | `5` | Numero massimo di file per batch |
| `MAX_BATCH_SIZE_MB` | `100` | Dimensione totale massima del batch |
| `MAX_PAGE_COUNT` | `50` | Numero massimo di pagine per PDF |
| `MAX_CONCURRENT_JOBS` | `1` | Conversioni simultanee; mantenere 1 su CPU |
| `OCR_TIMEOUT_SECONDS` | `300` | Timeout per singola richiesta al motore Ollama |
| `RENDER_DPI` | `72` | Risoluzione CPU-friendly delle sole pagine scansionate; usare 96-120 per scansioni difficili |
| `NATIVE_TEXT_MIN_CHARS` | `20` | Soglia per usare il text layer senza OCR |
| `JOB_TTL_SECONDS` | `3600` | Durata dei job completati/falliti in memoria |

## Setup Locale

Prerequisiti:

- Python 3.11+
- Nessun servizio cloud o processo OCR esterno per la modalità predefinita

Installazione iniziale da PowerShell, partendo dalla radice del portfolio:

```powershell
cd .\conversione-pdf-markdown-ai-coding\Script
python -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Avvio backend e frontend in modalità local-only:

```powershell
.\start.ps1
```

Se la policy PowerShell blocca lo script:

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

Aprire poi il browser su:

```text
http://127.0.0.1:8000
```

Il server resta attivo nella finestra PowerShell; per arrestarlo premere `Ctrl+C`.

## Motori OCR

La modalità raccomandata su PC senza GPU è già il default:

```powershell
$env:OCR_ENGINE="rapidocr"
```

RapidOCR usa modelli ONNX piccoli inclusi nelle dipendenze, resta interamente offline e nel test sintetico su Intel i3 ha completato una pagina scansionata in circa 7 secondi.

Ollama è opzionale. Può preservare meglio layout complessi, ma su un i3 1115G4 GLM-OCR Q8 può superare 5 minuti per pagina. Per abilitarlo:

```powershell
ollama pull glm-ocr:q8_0
$env:OCR_ENGINE="ollama"
```

Il backend chiama Ollama su `OLLAMA_BASE_URL` e usa il modello indicato in `OLLAMA_MODEL`.

Per verificare che Ollama risponda:

```powershell
curl http://localhost:11434/api/tags
```

Se il modello locale ha un nome diverso dal default, impostare la variabile prima dell'avvio:

```powershell
$env:OLLAMA_MODEL="nome-modello"
.\start.ps1
```

Ollama 0.17.1-0.17.5 presenta una regressione GLM-OCR che produce Markdown vuoto. Il client include il marker `[img-0]` compatibile con tali versioni e rifiuta comunque risultati vuoti; aggiornare Ollama appena possibile.

## Privacy e Gestione Stato

Il sistema non usa database. PDF, Markdown e stato dei job sono mantenuti esclusivamente in memoria:

- `queued`
- `processing`
- `completed`
- `failed`

I job completati o falliti vengono rimossi automaticamente dopo `JOB_TTL_SECONDS`.
Essendo tutto in memoria, un riavvio del server elimina tutti i job e i risultati non ancora scaricati.

I PDF non vengono scritti in file temporanei. Il frontend usa `sessionStorage`, non `localStorage`, e non salva il Markdown. Il pulsante **Elimina e ricomincia** cancella immediatamente job e risultato dalla RAM. Le risposte API impostano `Cache-Control: no-store`.

RapidOCR non effettua chiamate HTTP. In modalità Ollama sono accettati soltanto endpoint loopback e modelli senza `remote_host`; il client ignora inoltre i proxy di sistema. Non usare `ALLOW_REMOTE_OCR=true` per documenti riservati.

## Error Handling

Sono gestiti i principali casi di errore:

- file assente
- file non PDF
- PDF corrotto
- PDF protetto da password
- file oltre la dimensione massima
- PDF oltre il numero massimo di pagine
- motore OCR non disponibile
- conversione non ancora completata
- job inesistente
- OCR senza testo estraibile su una pagina

## Frontend

Il frontend è volutamente leggero e senza build step:

- HTML statico
- CSS dedicato
- JavaScript vanilla
- upload via `fetch`
- progress tracking via `EventSource`
- metadati job limitati alla scheda corrente tramite `sessionStorage`

## Test

La cartella `backend/tests` contiene test unitari e di integrazione per privacy, validazione, estrazione nativa, OCR e API.

Comando:

```powershell
cd .\conversione-pdf-markdown-ai-coding\Script\backend
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

PDF sintetici privi di dati reali:

```text
examples/sample_text.pdf
examples/sample_scanned.pdf
```

Possono essere rigenerati dalla cartella `Script` con:

```powershell
.\backend\.venv\Scripts\python.exe .\examples\generate_samples.py
```

## Scelte Progettuali

| Scelta | Motivazione |
|--------|-------------|
| FastAPI | API leggere, async nativo, integrazione semplice con frontend statico |
| PyMuPDF | Rendering PDF robusto e diretto lato server |
| RapidOCR + ONNX | OCR offline in pochi secondi su CPU senza GPU |
| Ollama opzionale | Qualità aggiuntiva per layout complessi quando l'hardware lo consente |
| Markdown come output | Formato leggibile da IDE, repository Git e agenti AI come Copilot, Codex e Claude Code |
| Job in memoria | Semplicità e nessuna dipendenza database |
| SSE | Progress tracking semplice senza WebSocket |
| Frontend vanilla | Nessun tooling frontend, avvio immediato |

