# Documentazione Tecnica — PDF to Markdown Converter

Web app locale per convertire PDF in Markdown pulito tramite OCR eseguito con Ollama. Il progetto è organizzato in un backend FastAPI e un frontend statico servito dallo stesso processo.

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
        ├── Rendering pagine con PyMuPDF
        ├── OCR pagina per pagina via Ollama
        ├── Assemblaggio Markdown
        ├── Stato job in memoria
        └── Download .md / .zip
```

## Struttura del Progetto

```text
Script/
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
│   │       ├── ocr_client.py       # Client HTTP verso Ollama
│   │       └── markdown_assembler.py
│   ├── tests/
│   ├── requirements.txt
│   └── pyproject.toml
└── frontend/
    ├── index.html
    ├── css/style.css
    ├── js/app.js
    └── assets/
```

## Pipeline di Conversione

1. **Upload**
   - L'utente carica uno o più PDF tramite interfaccia web.
   - Il backend verifica content type, magic bytes `%PDF-`, dimensione massima, protezione password e numero massimo di pagine.

2. **Creazione Job**
   - Ogni file genera un `ConversionJob` identificato da UUID.
   - Lo stato viene mantenuto in memoria tramite `JobManager`.

3. **Rendering**
   - `pdf_renderer.py` usa PyMuPDF per convertire ogni pagina in PNG.
   - Le immagini vengono codificate in base64 e passate al client OCR.

4. **OCR**
   - `ocr_client.py` invia ogni pagina a Ollama tramite `POST /api/generate`.
   - Le pagine vengono processate in modo sequenziale.

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
| `GET` | `/api/health` | Verifica disponibilità Ollama e modello configurato |
| `POST` | `/api/upload` | Carica un PDF e avvia una conversione |
| `POST` | `/api/upload/batch` | Carica più PDF e avvia job separati |
| `GET` | `/api/jobs/{job_id}/status` | Restituisce lo stato del job |
| `GET` | `/api/jobs/{job_id}/progress` | Stream SSE con avanzamento pagina per pagina |
| `GET` | `/api/jobs/{job_id}/preview` | Restituisce Markdown e warning |
| `GET` | `/api/jobs/{job_id}/download` | Scarica il risultato `.md` |
| `GET` | `/api/jobs/batch/download` | Scarica più risultati in formato `.zip` |

## Configurazione

Le variabili d'ambiente sono opzionali.

| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | URL base del servizio Ollama |
| `OLLAMA_MODEL` | `glm-ocr` | Modello OCR usato da Ollama |
| `MAX_FILE_SIZE_MB` | `50` | Dimensione massima per file |
| `MAX_PAGE_COUNT` | `200` | Numero massimo di pagine per PDF |
| `OCR_TIMEOUT_SECONDS` | `600` | Timeout per richiesta OCR |
| `RENDER_DPI` | `150` | Risoluzione rendering PDF → immagine |
| `JOB_TTL_SECONDS` | `3600` | Durata dei job completati/falliti in memoria |

## Setup Locale

Prerequisiti:

- Python 3.11+
- Ollama installato e avviato
- Modello OCR disponibile in Ollama

Esempio:

```powershell
cd conversione-pdf-markdown-ai-coding\Script\backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Avvio backend e frontend:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Aprire poi:

```text
http://localhost:8000
```

## Ollama

Il backend chiama Ollama su `OLLAMA_BASE_URL` e usa il modello indicato in `OLLAMA_MODEL`.

Per verificare che Ollama risponda:

```powershell
curl http://localhost:11434/api/tags
```

Se il modello locale ha un nome diverso dal default, impostare la variabile prima dell'avvio:

```powershell
$env:OLLAMA_MODEL="nome-modello"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Gestione Stato

Il sistema non usa database. Lo stato dei job è mantenuto in memoria:

- `queued`
- `processing`
- `completed`
- `failed`

I job completati o falliti vengono rimossi automaticamente dopo `JOB_TTL_SECONDS`.

Questa scelta rende il progetto semplice e adatto a uso locale o small-team, ma implica che i risultati non sopravvivono al riavvio del server.

## Error Handling

Sono gestiti i principali casi di errore:

- file assente
- file non PDF
- PDF corrotto
- PDF protetto da password
- file oltre la dimensione massima
- PDF oltre il numero massimo di pagine
- Ollama non disponibile
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
- persistenza client-side dell'ultimo job tramite `localStorage`

## Test

La cartella `backend/tests` è predisposta per test unitari e di integrazione.

Comando previsto:

```powershell
cd conversione-pdf-markdown-ai-coding\Script\backend
pytest
```

## Scelte Progettuali

| Scelta | Motivazione |
|--------|-------------|
| FastAPI | API leggere, async nativo, integrazione semplice con frontend statico |
| PyMuPDF | Rendering PDF robusto e diretto lato server |
| Ollama locale | OCR local-first, utile per documenti riservati |
| Markdown come output | Formato leggibile da IDE, repository Git e agenti AI come Copilot, Codex e Claude Code |
| Job in memoria | Semplicità e nessuna dipendenza database |
| SSE | Progress tracking semplice senza WebSocket |
| Frontend vanilla | Nessun tooling frontend, avvio immediato |

