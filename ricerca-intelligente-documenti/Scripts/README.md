# Documentazione Tecnica — Ricerca Intelligente Documenti

Architettura e logiche tecniche del sistema RAG (Retrieval-Augmented Generation) per l'interrogazione in linguaggio naturale di documenti amministrativi italiani.

> ⚠️ *Il codice sorgente non è incluso per motivi di riservatezza aziendale. Questa documentazione descrive le scelte architetturali, gli algoritmi e le logiche implementate.*

---

## Indice

1. [Panoramica dell'Architettura](#1-panoramica-dellarchitettura)
2. [Pipeline di Acquisizione Documenti](#2-pipeline-di-acquisizione-documenti)
3. [Indicizzazione e Chunking Semantico](#3-indicizzazione-e-chunking-semantico)
4. [Motore RAG — Retrieval e Generazione](#4-motore-rag--retrieval-e-generazione)
5. [Cross-Document Linking](#5-cross-document-linking)
6. [Version Tracking](#6-version-tracking)
7. [Generazione Automatica Schede Commessa](#7-generazione-automatica-schede-commessa)
8. [Infrastruttura e Utilities](#8-infrastruttura-e-utilities)
9. [Scelte Ingegneristiche Chiave](#9-scelte-ingegneristiche-chiave)

---

## 1. Panoramica dell'Architettura

Il sistema si compone di **5 macro-componenti** che operano in pipeline:

```
PDF Documenti
      │
      ▼
┌───────────────────────────┐
│  1. ACQUISIZIONE          │  Azure Document Intelligence (OCR + Layout)
│     Scansione + Struttura │
└────────────┬──────────────┘
             │  JSON strutturati
             ▼
┌───────────────────────────┐
│  2. INDICIZZAZIONE        │  Chunking semantico + Embedding vettoriale
│     Sync incrementale     │
└────────────┬──────────────┘
             │  Chunks + Embeddings
             ▼
┌───────────────────────────┐
│  3. ARRICCHIMENTO         │  Topic classification + Cross-doc linking
│     Version tracking      │  + Catene di versionamento
└────────────┬──────────────┘
             │
     ┌───────┴────────┐
     ▼                ▼
┌──────────┐   ┌──────────────────┐
│ 4. QUERY │   │ 5. GENERAZIONE   │
│    RAG   │   │    SCHEDE        │
└────┬─────┘   └───────┬──────────┘
     ▼                 ▼
 Risposta con      Scheda Commessa
 Citazioni         strutturata (14 sezioni)
```

**Stack tecnologico**: Python (async/await) · Azure OpenAI (GPT-4.1 + text-embedding-3-large) · Azure Document Intelligence · MongoDB (vector store + document store)

---

## 2. Pipeline di Acquisizione Documenti

### 2.1 Scansione OCR

I documenti PDF vengono processati tramite **Azure Document Intelligence** con il modello `prebuilt-layout`, che fornisce analisi strutturale completa (testo, tabelle, sezioni gerarchiche).

**Strategie implementate:**

- **Throttling preventivo**: le chiamate API sono intervallate con un ritardo fisso (~7 req/sec) per mantenersi sotto il limite di 15 TPS di Azure, evitando a monte i 429
- **Retry con backoff esponenziale**: su errori transitori o rate limiting, il sistema applica retry geometrico (1s → 2s → 4s → 8s → 16s) fino a 5 tentativi
- **Scansione ricorsiva**: discovery automatica dei PDF nelle directory configurate tramite `os.walk`

### 2.2 Elaborazione Strutturale

Il JSON grezzo di Azure viene trasformato in una **struttura semantica gerarchica**, pronta per il chunking.

**Logiche chiave:**

- **Ricostruzione gerarchica**: traversal ricorsivo DFS dell'albero delle sezioni con cycle detection tramite set di nodi visitati
- **Tracking pagine per paragrafo**: ogni paragrafo è mappato alla pagina sorgente tramite offset (span), non per indice — garantendo attribuzione precisa anche in documenti multi-pagina
- **Gestione contenuti orfani**: paragrafi non assegnati a nessuna sezione vengono coalesciti in una sezione sintetica ("Frontespizio o testo non assegnato")
- **Conversione tabelle**: ricostruzione matrice `righe × colonne` dalle celle Azure, con output in formato pipe-delimited leggibile
- **Deduplicazione**: set-based su contenuto dei paragrafi per evitare ripetizioni da sezioni sovrapposte

**Output**: un JSON per documento con sezioni, paragrafi localizzati per pagina, tabelle in formato testuale e metadati (ente, document_id univoco).

---

## 3. Indicizzazione e Chunking Semantico

### 3.1 Chunking

L'algoritmo di chunking è **section-aware**: rispetta i confini semantici del documento anziché tagliare a dimensione fissa.

**Parametri:**

| Parametro | Valore | Motivazione |
|-----------|--------|-------------|
| Dimensione target | 1.500 caratteri (~375 token) | Bilanciamento contesto/precisione per documenti amministrativi italiani |
| Overlap | 200 caratteri | Preserva contesto tra chunk adiacenti |
| Dimensione minima | 300 caratteri | Evita chunk troppo frammentati |
| Dimensione massima | 2.500 caratteri | Hard limit per il contesto LLM |

**Algoritmo:**

1. Ogni paragrafo diventa una `ParagraphUnit` con `(contenuto, pagina, block_id)`
2. **Accumulazione greedy**: le unità vengono aggregate per sezione fino al raggiungimento della dimensione target
3. **Split su frasi**: se una singola unità eccede il massimo, il taglio avviene su punteggiatura italiana (`.` `!` `?` `;` `:`) seguita da maiuscola o simbolo `€`
4. **Sliding window con overlap**: gli ultimi 200 caratteri del chunk precedente vengono riportati nel successivo
5. **Merge chunk piccoli**: chunk sotto la soglia minima vengono fusi con l'adiacente (se le pagine sono compatibili)
6. **Gestione sezioni sparse**: sezioni che coprono >3 pagine non contigue vengono prima raggruppate per pagina, poi chunkate per gruppo
7. **Filtraggio rumore**: scartati numeri di pagina isolati, singoli caratteri, contenuti non semantici

**Tracking pagine**: ogni chunk mantiene la lista esatta delle pagine dei paragrafi che contiene (non un range approssimativo), abilitando citazioni precise.

### 3.2 Embedding Vettoriale

Gli embedding sono generati con **Azure OpenAI `text-embedding-3-large`** (3.072 dimensioni).

- **Dual client**: client sincrono (per singole query) + client asincrono (per batch di indicizzazione)
- **Processamento parallelo**: batch con semaforo a 5 richieste concorrenti per evitare saturazione
- **Rate limiting integrato**: Token Bucket asincrono con limiti duali TPM/RPM (350K token/min, 350 req/min)
- **Stima token**: approssimazione 4 caratteri ≈ 1 token per l'italiano
- **Gestione errori granulare**: embedding falliti non bloccano il batch; vengono flaggati per retry successivo

### 3.3 Sincronizzazione Incrementale

Il sistema implementa **change detection** per evitare la rielaborazione di documenti invariati.

- **Hash SHA-256**: ogni documento viene hashato; al sync successivo, solo i file con hash diverso vengono riprocessati
- **Tre categorie**: nuovi (non in DB), modificati (hash cambiato), eliminati (in DB ma non su filesystem)
- **Operazioni atomiche**: upsert con `replace_one()` per garantire idempotenza
- **Processamento parallelo**: fino a 5 documenti elaborati in concorrenza
- **Cleanup automatico**: rimozione da MongoDB dei documenti non più presenti su filesystem

### 3.4 Persistenza MongoDB

**Collections principali:**

| Collection | Contenuto | Indici chiave |
|------------|-----------|---------------|
| `documents` | Metadati documento (ente, CIG, durata, hash) | `ente`, `gara.cig` |
| `chunks` | Chunk con embedding per ricerca vettoriale | `document_id`, `ente`, `macro_topic`, `tipo_contenuto` |
| `sources` | Mappatura block_id → pagina per citazioni | `block_id` (unique), `document_id`, `pagina` |
| `sync_status` | Stato sincronizzazione per change detection | `file_path` (unique) |
| `pending_references` | Riferimenti cross-doc non ancora risolti | `ente`, `status` |

**Block ID**: formato `{doc_id}|{section_id}|{type}_{index}|{hash}` — univoco, deterministico e debuggabile.

---

## 4. Motore RAG — Retrieval e Generazione

### 4.1 Parsing della Query

La query in linguaggio naturale viene analizzata per estrarre **intent** e **filtri strutturati**.

**Intent supportati:**

| Intent | Trigger | Esempio |
|--------|---------|---------|
| SINGOLO | (default) | "Qual è il CIG di Laterza?" |
| ELENCO | elenca, lista, tutti | "Elenca tutti i documenti" |
| CONTEGGIO | quanti, conta, totale | "Quanti contratti ci sono?" |
| COMPARAZIONE | confronta, differenza | "Confronta Laterza e Sorrento" |

**Estrazione ente (3 livelli)**:
1. Match diretto nel testo
2. Pattern regex: `"di/per/del comune di [ente]"`
3. Fuzzy matching con `difflib.SequenceMatcher` (cutoff 0.6) su ogni parola >3 caratteri

**Estrazione filtri**: il testo viene passato a un LLM (temperature 0.2 per determinismo) che estrae filtri strutturati — ente, CIG, date, durata — convertiti poi in operatori MongoDB (`$in`, `$lte`, `$gte`). Supporta date relative (es. `<OGGI+4_ANNI>`).

### 4.2 Retrieval Vettoriale

**Pipeline di retrieval a 3 stadi:**

1. **Ricerca per similarità coseno**: l'embedding della query viene confrontato con tutti i chunk (L2-normalizzati) tramite dot product. Soglia minima di similarità: **0.45** (più bassa dello standard 0.5, calibrata per il dominio amministrativo italiano dove la terminologia è meno semanticamente esplicita)

2. **Reranking LLM**: i 25 chunk candidati migliori vengono rivalutati da GPT-4.1 che li riordina per pertinenza alla query specifica. Vengono mantenuti i top 12

3. **Arricchimento contesto**: espansione del set con chunk correlati tramite il dependency resolver (vedi sezione 5)

### 4.3 Espansione con Dipendenze e Versioni

Il **Dependency Resolver** arricchisce i risultati primari tramite **BFS (Breadth-First Search)** sul grafo delle dipendenze pre-calcolate:

- **Profondità massima**: 3 livelli di traversal
- **Budget dinamico**: il numero di chunk aggiuntivi è proporzionale ai riferimenti espliciti trovati (0 riferimenti → 0 chunk extra; 1-2 → 4 chunk; 5+ → 8 chunk)
- **Priorità versioni**: i chunk da documenti nella stessa catena di versionamento vengono inseriti prima dei cross-doc generici
- **Prevenzione cicli**: set di nodi visitati per evitare loop nel grafo
- **Ri-scoring**: i chunk espansi vengono rivalutati per similarità coseno rispetto alla query
- **Limite assoluto**: massimo 20 chunk totali (12 primari + 8 espansi)

### 4.4 Generazione della Risposta

La risposta viene generata tramite **GPT-4.1** con un system prompt specializzato per documenti amministrativi italiani:

- **Grounding forzato**: il modello risponde esclusivamente sulla base dei chunk forniti; se l'informazione non è presente, lo dichiara esplicitamente
- **Citazioni inline**: formato `[N]` mappato a `(Documento, pag. X)` tramite il mapping block_id → pagina nella collection `sources`
- **Terminologia gare d'appalto**: regole esplicite per ribassi e percentuali (es. base 46% − ribasso 0,01% = aggio finale 45,99%)
- **Validazione grounding**: se la similarità media dei chunk è < 0.5, la risposta viene flaggata come `has_low_confidence`
- **Streaming**: la risposta viene streamata token per token nella GUI per feedback immediato all'utente

---

## 5. Cross-Document Linking

Il sistema rileva e gestisce **dipendenze tra documenti** — situazione comune nel dominio amministrativo dove un capitolato rimanda a determine, contratti e bandi correlati.

### 5.1 Estrazione Riferimenti Espliciti

**Approccio regex-based** che identifica 4 categorie di rimandi nel testo:

1. **Documenti nominati**: "come previsto nel Capitolato", "di cui alla Determina n. 417"
2. **Articoli e sezioni**: "art. 5", "comma 2", "punto 3.1"
3. **Connettori sintattici**: "ai sensi del", "di cui al", "come da"
4. **Sezioni standalone**: riferimenti a sezioni note nel contesto del documento corrente

**Normalizzazione alias**: ogni documento ha varianti canoniche (es. "Capitolato speciale d'oneri" → "capitolato") gestite tramite una pipeline di pulizia (lowercase, rimozione articoli, stripping punteggiatura, lookup sinonimi).

### 5.2 Risoluzione Dipendenze e Linking Semantico

Le dipendenze vengono risolte su **due livelli**:

**Esplicite** (alta confidenza):
- Matching del nome documento target tramite fuzzy matching a 3 stadi: alias esatto → word overlap ≥70% → contenimento alias più lungo
- Risoluzione sezione target tramite regex su titoli e contenuto dei chunk

**Implicite** (similarità semantica):
- Filtraggio MongoDB: stesso ente + stesso macro_topic + documento diverso
- Similarità coseno tra embedding con soglia **0.75** (molto più alta della retrieval, per minimizzare i falsi positivi)
- Massimo 5 dipendenze implicite per chunk

### 5.3 Gestione del Grafo

- **Bidirezionalità**: ogni link crea automaticamente il link inverso sul chunk/documento target
- **Aggregazione document-level**: link multipli chunk→chunk vengono coalesciti in un singolo link doc→doc (riduce ridondanza)
- **Pattern pending reference**: se un documento target non è ancora stato importato, il riferimento viene salvato come "pending" e risolto automaticamente al prossimo import
- **Cleanup su re-import**: le dipendenze stale vengono rimosse quando un documento viene reimportato

---

## 6. Version Tracking

Il sistema ricostruisce automaticamente la **storia evolutiva** di ogni gara/contratto: proroghe, rinnovi, rettifiche, integrazioni, successioni.

### 6.1 Estrazione Metadati

Dai primi 6.000 caratteri di ogni documento vengono estratti:

- **CIG**: pattern regex a 10 caratteri alfanumerici con almeno 1 cifra (filtro per evitare falsi positivi come parole maiuscole)
- **Determine citate**: pattern multipli per formati diversi (det. n. X del Y/Z/W, determina n. X, etc.)
- **Date**: parsing flessibile di formati italiani (DD/MM/YYYY, DD-MM-YYYY)
- **Tipo atto**: classificazione del documento (determina, capitolato, contratto, etc.)

**Strategia ibrida regex + LLM**: prima il regex (veloce, deterministico), poi fallback LLM solo se i segnali regex sono insufficienti.

### 6.2 Rilevamento Relazioni tra Documenti

Tre strategie di matching **in ordine di priorità**:

| Strategia | Confidenza | Logica |
|-----------|------------|--------|
| **CIG match** | 1.0 | Documenti che condividono lo stesso codice CIG |
| **Determina match** | 1.0 | La determina citata nel documento A corrisponde alla data della determina B |
| **Fuzzy oggetto** | 0.80–1.0 | `SequenceMatcher` sull'oggetto normalizzato (lowercase + stop word removal) con soglia 0.80 |

Se più segnali puntano allo stesso target, vengono fusi in una singola relazione con segnale "multiplo" e confidenza massima.

### 6.3 Classificazione del Tipo di Relazione

**Approccio keyword-based con fallback LLM:**

| Tipo relazione | Keyword trigger |
|----------------|-----------------|
| **Proroga** | prorog\*, prosecuzion\*, extension\* temporal\* |
| **Rinnovo** | rinnov\*, nuov\* procedur\*, nuov\* gara |
| **Rettifica** | rettific\*, correzion\*, modific\* |
| **Integrazione** | integrazion\*, est\* ex |
| **Successione** | sostituzion\*, subentr\*, nuov\* affidament\* |

**Regola di dominanza**: il tipo viene assegnato solo se il keyword più frequente ha ≥2× le occorrenze del secondo classificato. In caso di ambiguità, interviene l'LLM.

### 6.4 Catene di Versionamento

I documenti correlati vengono organizzati in **catene cronologiche**:

- **Chain ID**: derivato dal CIG (preferito, più stabile tra versioni) oppure dall'hash SHA-256 dell'oggetto normalizzato + ente (fallback deterministico)
- **Link bidirezionali**: ogni membro della catena ha puntatori `predecessore` e `successori[]`
- **Stato di vigenza**, calcolato automaticamente dai successori:
  - Ha un rinnovo/rettifica successore → **superato**
  - Ha una proroga/integrazione successore → **integrato**
  - Nessun successore → **vigente**
- **Cronologia ordinata**: i membri della catena vengono ordinati per `data_efficacia` ascendente per ricostruzione temporale
- **Ricalcolo dinamico**: la vigenza viene ricalcolata ogni volta che la catena viene aggiornata

---

## 7. Generazione Automatica Schede Commessa

Il sistema genera report strutturati ("Schede Commessa") interrogando automaticamente l'archivio RAG con prompt specializzati per sezione.

### 7.1 Architettura del Generatore

- **14 sezioni tematiche** configurate in un file JSON esterno (titolo, prompt RAG, formato output, campi richiesti)
- **Processamento sequenziale**: le sezioni vengono elaborate una alla volta per rispettare i limiti di rate delle API
- **Inizializzazione lazy**: il motore RAG viene creato solo alla prima sezione (risparmio risorse)
- **Resilienza agli errori**: il fallimento di una sezione non blocca il batch; la sezione viene marcata come "non_disponibile"

### 7.2 Processing per Sezione

Per ogni sezione il sistema:

1. Invia al motore RAG un **prompt specializzato** (es. per la sezione "Aggio": estrai base di gara, ribasso, calcola aggio finale, cerca corrispettivi e premi)
2. Riceve la risposta con citazioni inline `[N]`
3. **Formatta l'output** in base al tipo configurato:
   - **Tabella**: parsing di coppie chiave-valore → tabella Markdown
   - **Lista**: normalizzazione a bullet points con prefisso `-`
   - **Discorsivo**: preservazione prosa con collassamento newline superflui
4. **Estrae e formatta le citazioni** con consolidamento range pagine

### 7.3 Qualità e Stato

Ogni sezione riceve uno **stato di qualità**:

| Stato | Condizione |
|-------|------------|
| **Completata** | ≥3 chunk utilizzati + nessun flag di bassa confidenza |
| **Parziale** | <3 chunk oppure flag di bassa confidenza |
| **Non disponibile** | Errore nel processamento o nessun chunk rilevante |

### 7.4 Output Finale

Il documento Markdown generato include:

- **Indice navigabile** con link a ogni sezione
- **14 sezioni** con contenuto formattato e citazioni inline
- **Appendice**: tabella riepilogativa di tutti i documenti fonte con le pagine citate
- **Metadati**: data generazione, numero documenti analizzati, versione generatore

La conversione in PDF è supportata tramite container Docker.

---

## 8. Infrastruttura e Utilities

### 8.1 Rate Limiting — Token Bucket Asincrono

Implementazione di un **Token Bucket dual** (TPM + RPM) per gestire i limiti delle API Azure OpenAI:

- **Limiti separati** per embedding (350K TPM, 350 RPM) e LLM (10K TPM, 60 RPM)
- **Prenotazione asincrona**: `wait_and_reserve()` attende disponibilità prima di effettuare la chiamata
- **Rilascio token non usati**: se la stima token era eccessiva, i token vengono rilasciati

### 8.2 Retry con Backoff Esponenziale

Strategia di retry per tutte le chiamate API Azure:

| Tentativo | Attesa | Note |
|-----------|--------|------|
| 1 | 1s | Primo retry rapido |
| 2 | 2s | Backoff geometrico |
| 3 | 4s | — |
| 4 | 61s | Reset completo della finestra rate limit |
| 5 | — | `RetryExhaustedError` |

Eccezioni gestite: `RateLimitError` (429), `APIError`, `APIConnectionError`, `ConnectionError`, `TimeoutError`.

### 8.3 Orchestrazione Batch

Lo script `auto_update.py` orchestra l'intero processo di aggiornamento in **4 step**:

1. **Setup indici** MongoDB (idempotente — skip se esistono già)
2. **Sincronizzazione documenti** (incrementale o force-clean)
3. **Classificazione topic batch**: chunk con `macro_topic` nullo vengono classificati dall'LLM in batch da 20
4. **Calcolo dipendenze cross-doc**: BFS + linking semantico

Supporta **checkpoint recovery** (timestamp `deps_computed_at`) per restart sicuro dopo interruzioni, e flag `--skip-topics`, `--skip-deps`, `--ente` per esecuzioni parziali.

### 8.4 Interfaccia Utente

GUI basata su **Tkinter** con:

- **Streaming** della risposta token per token (threading per non bloccare la UI)
- **Color coding**: query utente (blu), risposta bot (grigio), errori (rosso), warning (arancione), citazioni (verde)
- **Logging asincrono**: le query vengono loggate in MongoDB in background (non-blocking)

---

## 9. Scelte Ingegneristiche Chiave

| Aspetto | Decisione | Motivazione |
|---------|-----------|-------------|
| Soglia similarità retrieval | **0.45** | I documenti amministrativi italiani sono meno semanticamente espliciti dello standard |
| Soglia similarità cross-doc | **0.75** | Standard più alto per evitare falsi positivi nelle dipendenze implicite |
| Soglia fuzzy oggetto (versioning) | **0.80** | Bilanciamento recall/precision per matching tra titoli di gare |
| Top-K chunk retrieval | **12** (fino a 20 con espansione) | Contesto sufficiente senza saturare la finestra LLM |
| Chunk size | **1.500 char** (~375 token) | Calibrato per la lunghezza media delle clausole italiane |
| Reranking | **25 candidati → 12 finali** | L'LLM migliora significativamente l'ordine rispetto alla sola cosine similarity |
| Chain ID | **CIG preferito**, fallback hash oggetto | Il CIG è il collegamento più stabile tra versioni di una stessa gara |
| Vigenza | **Calcolata dai successori** | Logica deterministica: nessun successore = vigente |
| Strategia ibrida regex/LLM | **Regex first, LLM fallback** | Velocità e determinismo dove possibile, LLM solo per ambiguità |
| Embedding concorrenza | **Semaforo a 5** | Parallelismo senza saturare il rate limit |
| Change detection | **SHA-256 per file** | Riprocessa solo documenti effettivamente modificati |
| Budget cross-doc dinamico | **Proporzionale ai riferimenti** | 0 ref → 0 extra; 1-2 ref → 4 chunk; 5+ ref → 8 chunk |

---

> ⚠️ *Codice sorgente non disponibile per motivi di riservatezza aziendale.*
