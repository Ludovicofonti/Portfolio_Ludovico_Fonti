# RAG Scheda Generator

Sistema di **generazione automatica di schede di sintesi contrattuale** per enti della pubblica amministrazione italiana, basato su una pipeline di Retrieval-Augmented Generation (RAG).

Il sistema interroga semanticamente un corpus di documenti contrattuali indicizzati, estrae le informazioni rilevanti sezione per sezione tramite un LLM, e produce un documento strutturato con citazioni verificabili verso i documenti sorgente.

---

## Architettura

```
┌──────────────────────────────────────────────────────────┐
│                      CLI (argparse)                      │
│            crea_scheda_rag.py — entry point              │
└──────────────┬───────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────┐
│               SchedaGenerator (orchestratore)            │
│  ┌──────────────┐┌────────────────┐┌─────────────────┐   │
│  │ ConfigLoader ││SectionProcessor││CitationFormatter│   │
│  └─────┬────────┘└───────┬────────┘└──────────┬──────┘   │
│        │                 │                    │          │
│        ▼                 ▼                    ▼          │
│  sezioni.json    RAGEngine.query()    [N] → (Doc, pag.)  │
└──────────────────────────┬───────────────────────────────┘
                           │
                           ▼
               ┌───────────────────┐
               │     MongoDB       │
               │ (document chunks  │
               │  + embeddings)    │
               └───────────────────┘
```

### Pipeline RAG in tre fasi

1. **Retrieval** — Per ciascuna sezione tematica, il prompt viene inviato al RAG engine che esegue una ricerca per similarità vettoriale sui chunk documentali, filtrati per ente.
2. **Generation** — I chunk recuperati vengono passati come contesto all'LLM, che genera una risposta strutturata con marker di citazione inline.
3. **Post-processing** — I marker vengono risolti in citazioni leggibili nel formato strutturato. L'output viene adattato al formato dichiarato dalla sezione.

---

## Stack tecnologico

| Componente | Tecnologia |
|------------|-----------|
| Linguaggio | Python 3.11+ (async), Node.js |
| LLM | Azure OpenAI — GPT-4 |
| Vector Store | Vector database |
| Conversione PDF | Puppeteer (headless Chrome) via Docker |
| Configurazione | JSON (sezioni), variabili d'ambiente (credenziali) |
| CLI | Framework command-line con exit code strutturati |

---

## Architettura modulare

Il sistema è organizzato attorno a componenti ben definiti:

**Orchestratore**
- Inizializzazione del RAG engine (lazy loading)
- Validazione dell'ente e delle sezioni
- Iterazione sul set di sezioni
- Assemblaggio e salvataggio del documento finale
- Gestione di backup e protezione da sovrascritture

**Processore di Sezione**
- Invio della query RAG per ciascuna sezione
- Estrazione delle citazioni dalla risposta
- Formattazione dell'output secondo il tipo della sezione
- Determinazione dello stato di completamento

**Formattatore Citazioni**
- Risoluzione dei marker di citazione inline
- Formattazione dei range di pagine
- Aggregazione dei riferimenti per documento
- Generazione della tabella di appendice

**Config Manager**
- Caricamento e validazione della configurazione
- Normalizzazione dei nomi enti per il filesystem
- Gestione della coerenza schema

**Modelli di Dominio**
- Strutture tipizzate per citazioni e sezioni
- Documento scheda con metodi di serializzazione
- Risultati batch

**Gerarchia Eccezioni**
- Eccezioni specializzate per dominio
- Attributi contestuali strutturati

---

## Design pattern e scelte progettuali

- **Strategy** — Adattamento della formattazione dell'output in base al tipo della sezione (tabella / lista / testo)
- **Facade** — Un singolo punto d'ingresso che nasconde RAG engine, config e processing
- **Lazy Initialization** — Il RAG engine viene istanziato solo al primo accesso
- **Bulkhead** — Ogni sezione viene processata in isolamento; fallimenti in una sezione non bloccano le altre
- **Template Method** — Assemblaggio del documento finale secondo una struttura fissa: header → indice → sezioni → appendice
- **Credential Masking** — Sanitizzazione delle informazioni sensibili nei messaggi di errore
- **Graceful Degradation** — Sezioni non disponibili vengono sostituite con placeholder

---

## Strategia di error handling

Il sistema implementa una gestione degli errori a più livelli:

- **Errori a livello di sezione**: Catturati e sostituiti con un placeholder — la generazione prosegue per le sezioni rimanenti
- **Errori a livello batch**: Gli enti falliti vengono collezionati e il CLI ritorna informazioni di successo parziale
- **Rate limiting**: Gestione reattiva con retry e backoff esponenziale
- **Protezione sovrascrittura**: File esistenti generano backup automatico con timestamp

---

## Formato di output

Il documento generato è strutturato in:

1. **Header** — Titolo con nome ente, timestamp di generazione, numero di documenti analizzati, versione del generatore
2. **Indice** — Indice linkato delle sezioni + appendice
3. **Sezioni tematiche** — Ciascuna con contenuto nel formato appropriato (tabella / lista / paragrafo), citazioni inline, footer con fonti aggregate, indicatori di stato
4. **Appendice** — Tabella riepilogativa di tutti i documenti citati con i range di pagine

La conversione PDF opzionale (via Docker + Puppeteer) applica uno stile professionale con formatting, tabelle e citazioni formattate.

---

## Conversione PDF

La conversione opzionale verso formato PDF avviene in un container Docker:

- Scansione della directory di output per documenti generati
- Conversione in HTML tramite motore di markdown
- Rendering in PDF A4 con motore headless browser
- CSS personalizzato per formatting professionale
- Idempotente: salta file già elaborati

---

## Configurazione

Il sistema è configurabile tramite:

**Configurazione Sezioni**
- Definizione delle sezioni tematiche
- Prompt RAG specifico per l'estrazione di ciascuna sezione
- Formato di output (tabella / lista / discorsivo)
- Colonne e campi richiesti (per la validazione)
- Metadati e versionamento

**Validazione della Configurazione**
- Coerenza dello schema: numero di sezioni, nessun duplicato di codice/ordine
- Lunghezza minima dei prompt
- Coerenza formato-colonne
- Versionamento semantico

---

## Struttura del progetto

```
Generatore Schede/
├── config/
│   └── Configurazione sezioni (prompt, formato, validazione)
├── core/
│   ├── Orchestratore principale
│   ├── Processore di sezione via RAG
│   ├── Formattatore di citazioni
│   ├── Config manager
│   ├── Modelli di dominio
│   └── Gerarchia eccezioni
├── output/
│   ├── Schede generate
│   └── PDF convertiti (opzionale)
└── requirements
```
