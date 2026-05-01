# 🔍 Ricerca Intelligente nei Documenti Aziendali

## 📌 Contesto

Gestione quotidiana di volumi massivi di documenti critici — contratti, bandi di gara, offerte, capitolati — contenenti clausole soggette a penali, con rischio operativo elevato in caso di errore. Nessuno strumento equivalente era presente in azienda.

## 🎯 Obiettivo

Sviluppare un motore di ricerca in linguaggio naturale che consenta di interrogare l'archivio documentale aziendale, fornendo risposte precise con citazioni alle fonti originali.

## 🏗️ Soluzione

Sistema di **ricerca intelligente basato su AI** per interrogare in linguaggio naturale archivi documentali eterogenei (PDF, Word). Il sistema:

- Risponde **esclusivamente sulla base dei documenti indicizzati**, eliminando il rischio di allucinazioni
- Fornisce **citazioni alle fonti originali** per ogni risposta
- Riconosce automaticamente le **dipendenze tra documenti** e clausole
- Implementa **validazione incrociata** e **versionamento documentale**

## 🧰 Tech Stack

`Python` · `Azure OpenAI (GPT-4.1 + text-embedding-3-large)` · `MongoDB` · `Azure Document Intelligence`

## 📈 Impatto

| Metrica | Risultato |
|---------|-----------|
| Tempi di recupero informazioni | **−50%** |
| Rischi operativi da errore documentale | **Azzerati** |
| Copertura documentale | Contratti, bandi, offerte, capitolati |

## 👤 Ruolo

Unica risorsa Data Science sul progetto. Progettazione e sviluppo autonomo dell'intera architettura RAG con Azure OpenAI.

---

## 🔄 Come Funziona — Pipeline end-to-end

Il sistema si articola in **3 fasi principali**, dalla scansione del documento cartaceo/PDF fino alla risposta in linguaggio naturale con citazioni puntuali.

### Fase 1 — Acquisizione e Strutturazione Documenti

I documenti PDF (contratti, capitolati, determine, bandi) vengono scansionati tramite **Azure Document Intelligence** (OCR avanzato con modello `prebuilt-layout`) e trasformati in strutture semantiche organizzate:

- **Scansione OCR**: estrazione automatica di testo, tabelle, struttura delle sezioni, con gestione del rate limiting verso le API Azure
- **Elaborazione strutturale**: ricostruzione della gerarchia del documento (articoli, paragrafi, tabelle), tracking preciso delle pagine sorgente, gestione di paragrafi orfani

**Output**: un JSON strutturato per ogni documento, con sezioni, paragrafi localizzati per pagina e tabelle convertite in formato leggibile.

### Fase 2 — Indicizzazione Intelligente e RAG

I documenti strutturati vengono indicizzati in **MongoDB** per abilitare la ricerca semantica:

- **Chunking semantico**: suddivisione in blocchi di ~1.500 caratteri con overlap, preservando l'attribuzione alla pagina originale
- **Embedding vettoriale**: generazione di embeddings con `text-embedding-3-large` di Azure OpenAI per ricerca per similarità
- **Sincronizzazione incrementale**: rilevamento automatico di documenti nuovi, modificati o rimossi tramite hash SHA-256, con processamento parallelo
- **Cross-document linking**: collegamento automatico tra documenti correlati (es. un capitolato e la relativa determina) sia per rimandi espliciti che per affinità semantica
- **Version tracking**: ricostruzione della storia di ogni gara — proroghe, rinnovi, rettifiche, integrazioni — tramite CIG, determine e fuzzy matching, con indicazione dello stato di vigenza

**Interrogazione in linguaggio naturale**: l'utente pone domande in italiano ("Quali penali prevede il contratto di Laterza?") e il sistema:

1. Analizza la query ed estrae filtri (ente, CIG, date)
2. Recupera i chunk più rilevanti tramite ricerca vettoriale + reranking LLM
3. Arricchisce il contesto con documenti collegati e versioni correlate
4. Genera una risposta ancorata ai documenti con **citazioni puntuali** (documento + pagina)
5. Valida il grounding per evitare risposte non supportate dai dati

### Fase 3 — Generazione Automatica Schede Commessa

Il sistema genera automaticamente **Schede Commessa strutturate** — report di sintesi per ogni ente/gara — interrogando semanticamente l'archivio indicizzato:

- **14 sezioni tematiche** conformi al template aziendale: dati committente, date e durata, CIG e importi, oggetto, disposizioni generali, procedure operative, obblighi del committente, addebito spese, penali e sanzioni, remunerazione/aggio, software e banche dati, servizi e personale, rendicontazione, post-contratto
- **Citazioni verificabili**: ogni dato è accompagnato da "(Documento, pag. X)"
- **Modalità batch**: generazione per tutti gli enti in una singola esecuzione
- **Conversione PDF**: output Markdown convertibile in PDF tramite Docker

**Esempio di output**: una scheda che sintetizza automaticamente importi, ribassi, penali, scadenze e obblighi contrattuali da decine di pagine di documenti diversi — con riferimento puntuale alla fonte per ogni informazione.

---

## 🏛️ Architettura

```
PDF Documenti
     │
     ▼
┌─────────────────────────┐
│  Azure Doc Intelligence │  ← OCR + Layout Analysis
│  (prebuilt-layout)      │
└────────────┬────────────┘
             │ JSON strutturati
             ▼
┌─────────────────────────┐
│  Elaborazione Semantica │  ← Sezioni, paragrafi, tabelle
│  + Chunking             │     con tracking pagine
└────────────┬────────────┘
             │ Chunks + Embeddings
             ▼
┌─────────────────────────┐
│  MongoDB                │  ← documents, chunks, sources
│  (Vector Store)         │     sync_status, dependencies
└────────────┬────────────┘
             │
     ┌───────┴───────┐
     ▼               ▼
┌──────────┐  ┌──────────────────┐
│ Query    │  │ Scheda Generator │
│ RAG      │  │ (14 sezioni)     │
│ Engine   │  │                  │
└────┬─────┘  └────────┬─────────┘
     │                 │
     ▼                 ▼
 Risposta con      Scheda Commessa
 Citazioni         Markdown/PDF
```

---

> ⚠️ *Codice sorgente non disponibile per motivi di riservatezza aziendale.*
