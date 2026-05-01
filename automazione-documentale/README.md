# 📄 Automazione Documentale

## 📌 Contesto

La gestione delle commesse in ambito tributi locali genera un volume elevato di documentazione contrattuale: capitolati, disciplinari, determine di aggiudicazione, atti integrativi. Da questa documentazione devono essere prodotti due documenti operativi fondamentali:

- **Scheda Commessa** — sintesi strutturata che raccoglie le informazioni chiave di ogni commessa (clausole critiche, scadenze, penali, aggio, requisiti tecnici, dati di fatturazione), utilizzata come riferimento rapido durante la gestione operativa.
- **Nomina GDPR (ex art. 28)** — atto di designazione del Responsabile del trattamento dei dati personali, documento legale obbligatorio il cui contenuto varia in funzione delle specifiche contrattuali di ogni commessa.

La compilazione manuale di entrambi i documenti richiedeva l'analisi di **centinaia di pagine** per singola commessa, con tempi elevati, alto rischio di errore e difficoltà nel mantenere coerenza tra fonti diverse.

## 🎯 Obiettivo

Automatizzare la produzione di Schede Commessa e Nomine GDPR attraverso una pipeline AI che:

1. **Digitalizzi e indicizzi** la documentazione contrattuale tramite OCR e vector search
2. **Estragga automaticamente** le informazioni rilevanti per ciascuna sezione dei documenti target
3. **Generi documenti pronti per la revisione**, mantenendo sempre il controllo finale da parte dell'operatore

## 🏗️ Architettura

Il sistema è composto da tre moduli indipendenti che condividono la stessa base documentale:

### Pipeline di indicizzazione

Converte la documentazione contrattuale grezza in una knowledge base interrogabile:

- **OCR** con Azure Document Intelligence (modello `prebuilt-layout`) per estrarre testo strutturato dai PDF
- **Elaborazione** in chunk semantici con metadati (pagina, documento, ente)
- **Embedding** con `text-embedding-3-large` e indicizzazione su **MongoDB** con ricerca vettoriale

### Generatore Scheda Commessa

Produce una sintesi strutturata in Markdown per ciascuna commessa, organizzata in **14 sezioni tematiche** configurabili (dati ente, date contrattuali, importi, penali, obblighi, rendicontazione, ecc.):

- Interrogazione semantica della knowledge base sezione per sezione
- Generazione del contenuto con citazioni inline alle fonti (`Documento, pag. X`)
- Output in formati diversi per sezione: tabella, testo discorsivo, lista strutturata
- Appendice automatica con l'elenco dei documenti fonte consultati

### Generatore Nomina GDPR

Produce l'atto di designazione del Responsabile del trattamento a partire da un template DOCX, con un'architettura a **due fasi**:

- **Fase 1 — Estrazione**: per ciascuna delle 7 sezioni variabili del documento, il sistema recupera i chunk rilevanti via vector search e un LLM con prompt specializzato in ambito GDPR estrae i dati in formato strutturato (JSON con citazioni)
- **Fase 2 — Compilazione contestuale**: i dati estratti vengono integrati nel flusso del documento tramite un secondo passaggio LLM che genera testo sintatticamente coerente con il contesto circostante (paragrafi precedenti e successivi)
- Risoluzione automatica dei dati anagrafici dell'ente (CSV → estrazione AI → fallback)
- Output finale in DOCX con le sezioni variabili compilate

### Flusso dati

```
PDF contratti ──► OCR (Azure Document Intelligence)
                        │
                        ▼
                Elaborazione in chunk + embedding
                        │
                        ▼
                MongoDB (vector search)
                   │              │
                   ▼              ▼
          Scheda Commessa    Nomina GDPR
           (Markdown)         (DOCX)
```

## 🧰 Tech Stack

`Python` · `Azure OpenAI (GPT-4.1)` · `Azure Document Intelligence` · `Embeddings (text-embedding-3-large)` · `MongoDB (vector search)` · `RAG` · `python-docx`

## 📈 Risultati

| Metrica | Valore |
|---------|--------|
| Tempo di produzione per documento | **~5 minuti** (da diverse ore di lavoro manuale) |
| Riduzione del lavoro ripetitivo | **>95%** |
| Pagine analizzate per commessa | **200+** |
| Sezioni Scheda Commessa | 14 sezioni tematiche configurabili |
| Sezioni variabili Nomina GDPR | 7 sezioni con compilazione contestuale |
| Tracciabilità | Citazioni inline con riferimento a documento e pagina |

## 👤 Ruolo

Progettazione dell'architettura, sviluppo completo dei tre moduli e integrazione con il sistema RAG aziendale.
