# Generatore Nomina GDPR

Sistema di **generazione automatica di documenti legali GDPR** (art. 28 — Nomina del Responsabile del Trattamento) in formato DOCX, a partire da documentazione contrattuale digitalizzata e indicizzata in MongoDB.

Il sistema combina OCR documentale, ricerca semantica vettoriale e generazione LLM in un'architettura a due fasi disaccoppiate, producendo documenti legali compilati automaticamente con dati estratti dai contratti di servizio.

---

## Architettura

Il sistema opera con un'architettura a **due fasi indipendenti**, ciascuna con un motore LLM dedicato:

```
┌──────────────────────────────────────────────────────────────────────┐
│                      CLI (Command Line)                              │
│      Generazione con parametri: --extract | --compile                │
└──────────────────┬───────────────────────────┬───────────────────────┘
                   │                           │
      ┌────────────▼────────────┐  ┌───────────▼───────────────┐
      │  FASE 1 — ESTRAZIONE    │  │  FASE 2 — COMPILAZIONE    │
      │                         │  │                           │
      │  Engine Estrazione      │  │  Template Processor       │
      │  ├── Vector search      │  │  ├── Mapping dati         │
      │  ├── Query semantica    │  │  ├── Popolamento tabelle  │
      │  └── LLM (GPT-4+)       │  │  └── Normalizzazione      │
      │         │               │  │          │                │
      │  Data Processing        │  │  Compilatore (alt.)       │
      │  ├── Parsing JSON       │  │  └── Inserimento          │
      │  ├── Scoring qualità    │  │     contestuale           │
      │  └── Smart retry        │  │                           │
      └────────┬────────────────┘  └──────────┬────────────────┘
               │                              │
               ▼                              ▼
     Dati estratti (JSON)            Documento DOCX
          (intermedio)                   (finale)
```

Le due fasi sono **disaccoppiate tramite un artefatto JSON intermedio**, permettendo:
- Riesecuzione indipendente di ciascuna fase
- Debug e ispezione dei dati estratti prima della compilazione
- Sostituzione del template senza ri-estrazione

---

## Pipeline di preparazione documentale

A monte della generazione, la preparazione dei documenti sorgente avviene in **3 step sequenziali**:

```
PDF (Documenti contrattuali)
        │
        ▼  Step 1 — OCR
Estrazione testo e struttura
        │
        ▼  Step 2 — Elaborazione
Trasformazione strutturale: sezioni, paragrafi, tabelle, metadati
        │
        ▼  Step 3 — Indicizzazione
Vector Store (chunks + embeddings)
```

- **Step 1**: OCR con retry automatico e gestione errori di connessione
- **Step 2**: Trasformazione da formato grezzo a struttura normalizzata (risoluzione gerarchie, estrazione metadati, validazione integrità)
- **Step 3**: Chunking semantico, embedding vettoriale e caricamento in vector store

Ogni step è skipabile e supporta modalità dry-run e force-clean per operazioni di manutenzione.

---

## Stack tecnologico

| Componente | Tecnologia |
|------------|-----------|
| Linguaggio | Python 3.11+ (async) |
| LLM | Azure OpenAI — GPT-4 |
| Embeddings | Vector embeddings (modelli proprietari) |
| OCR | Servizi OCR cloud |
| Vector Store | Vector database |
| Generazione Documenti | Librerie di manipolazione documenti |
| Rate Limiting | Token bucket asincrono (TPM + RPM) |
| Configurazione | JSON (configurazione), CSV (anagrafica), variabili d'ambiente (credenziali) |

---

## Architettura modulare

Il sistema è organizzato attorno a componenti ben definiti:

**Componente di Orchestrazione**
- Gestisce l'intero workflow a due fasi
- Coordina operazioni batch
- Serializzazione e backup dei dati intermedi

**Engine di Estrazione (Fase 1)**
- Ricerca vettoriale su vector store
- Query semantica dei documenti
- Generazione risposte tramite LLM con prompt specializzato per contesto giuridico
- Estrazione delle citazioni dai risultati

**Data Processing**
- Parsing strutturato dei risultati
- Rilevamento e gestione valori mancanti
- Scoring di qualità e affidabilità
- Retry intelligente per risultati parziali

**Template Processor (Fase 2)**
- Identificazione delle sezioni variabili nel documento
- Mapping dei dati estratti alle posizioni corrette
- Popolamento dinamico di tabelle e liste
- Normalizzazione della formattazione finale

**Compilatore Alternativo**
- Strategia di inserimento contestuale
- Integrazione naturale del testo nel documento
- Gestione delle dipendenze tra sezioni

**Registry di Dominio**
- Fallback chain a 3 livelli per risoluzione dei dati
- Graceful degradation in caso di dati mancanti

**Utilità Condivise**
- Rate limiting asincrono (TPM + RPM)
- Backoff esponenziale per gestione errori transitori
- Client per servizi cloud

---

## Design pattern

| Pattern | Applicazione |
|---------|-------------|
| **Two-Phase Pipeline** | Estrazione e compilazione disaccoppiate tramite artefatto intermedio per indipendenza di esecuzione |
| **Strategy** | Due strategie di compilazione: mapping diretto vs. inserimento contestuale con LLM |
| **3-Tier Fallback** | Risoluzione dati con chain di fallback — degradazione graceful per dati mancanti |
| **Lazy Initialization** | Componenti critici istanziati solo al primo utilizzo |
| **Token Bucket** | Rate limiting asincrono con bucket separati per embedding e LLM |
| **Domain Exception Hierarchy** | Eccezioni specializzate per dominio con dati contestuali strutturati |
| **Credential Masking** | Sanitizzazione delle informazioni sensibili nei messaggi di errore |
| **Structured Logging** | Log strutturati con correlation ID, componente, timing e metriche di consumo |
| **Graceful Degradation** | Fallback a placeholder per sezioni non estraibili — completamento del documento comunque garantito |

---

## Strategia di resilienza

Il sistema implementa meccanismi di resilienza a più livelli:

### Rate limiting
- **Proattivo**: Ritardo preventivo per richieste che eccederebbero i limiti TPM/RPM
- **Reattivo**: Backoff esponenziale su errori di rate limit, connessione e timeout
- **Strategia di recovery**: Retry finale con attesa estesa per sopravvivere a finestre di throttling

### Estrazione dati
- **Smart retry**: Se la ricerca vettoriale individua documenti rilevanti ma l'LLM restituisce risultati incompleti, il sistema re-interroga con istruzioni adattate
- **Degradazione graceful**: Sezioni non estraibili vengono marcate come parziali — il documento viene comunque generato

### Gestione file
- File esistenti generano backup automatico con timestamp (flag `--force`)
- In caso di file bloccati, il sistema scrive su un path alternativo

### Validazione ai confini
- Configurazione validata al caricamento (schema, campi obbligatori)
- Risorse verificate prima dell'esecuzione
- Validazione degli input prima di operazioni critiche

---

## Sistema di configurazione

Il sistema è configurabile tramite file di configurazione strutturati:

**Configurazione Sezioni**
- Definisce le sezioni variabili del documento
- Prompt specifico per l'estrazione di ciascuna sezione
- Schema che l'LLM deve rispettare nella risposta
- Tipo di contenuto (testo, lista, tabella)
- Flag di obbligatorietà e comportamento di fallback
- Finestra di contesto per il processamento

**Registry Anagrafica**
- Dati pre-caricati degli enti
- Informazioni identificative e di contatto
- Dati dell'organo responsabile
- Lookup case-insensitive e tollerante ai typo

**Impostazioni Globali**
- Parametri LLM e rate limiting
- Credenziali (da variabili d'ambiente)

---

## Formato di output

Il sistema produce due artefatti per ente:

**Artefatto Intermedio (JSON)**
- Metadati: ente, timestamp, tempo di elaborazione, sorgenti documentali
- Dati anagrafici risolti
- Risultati per sezione con contenuto strutturato
- Stato di completamento (compilato / parziale / non trovato)
- Score di confidenza e citazioni con riferimenti documentali

**Documento Finale (DOCX)**
- Documento legale formattato secondo template
- Sezioni variabili compilate con dati estratti
- Formattazione normalizzata e pulita
- Tabelle e liste popolate dinamicamente
- Blocchi firma con identificativi e data di generazione
