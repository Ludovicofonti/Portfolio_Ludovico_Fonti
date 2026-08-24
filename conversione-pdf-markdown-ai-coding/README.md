# 📄 PDF to Markdown Converter

## 📌 Contesto

Molte informazioni operative, contrattuali e amministrative sono ancora distribuite in PDF difficili da riutilizzare: scansioni, documenti con layout complessi, tabelle poco leggibili, esportazioni da software gestionali o file con formattazione non uniforme.

Questi documenti sono spesso consultabili a video, ma poco adatti a essere integrati in workflow moderni: knowledge base, sistemi RAG, documentazione tecnica, automazioni AI, repository Git o strumenti di editing Markdown.

In particolare, la conversione in Markdown rende i contenuti più facilmente **navigabili, indicizzabili e modificabili da strumenti AI per lo sviluppo e l'analisi documentale** come GitHub Copilot, Codex, Claude Code e altri agenti coding. Un PDF resta un contenitore rigido; un file `.md`, invece, può essere letto, cercato, citato, versionato e rielaborato direttamente dagli strumenti che lavorano sul codice e sulla documentazione.

## 🎯 Obiettivo

Realizzare una web app locale che trasformi PDF "sporchi" o scansionati in file Markdown puliti, leggibili e riutilizzabili, riducendo il lavoro manuale di trascrizione, copia-incolla e riformattazione.

Il progetto abilita un flusso semplice:

1. Caricamento di uno o più PDF da interfaccia web
2. Estrazione del text layer oppure OCR locale delle sole pagine scansionate
3. Generazione di un documento Markdown consolidato
4. Anteprima del risultato
5. Download del file `.md` o di un archivio `.zip` in caso di conversione batch

## 🏗️ Soluzione

La soluzione è una **web app local-first** per convertire documenti PDF in Markdown strutturato. Per le scansioni usa RapidOCR/ONNX su CPU; Ollama con GLM-OCR resta una modalità opzionale per layout complessi.

Il sistema:

- Accetta PDF singoli o multipli tramite drag-and-drop
- Estrae direttamente il testo quando il PDF contiene già un text layer
- Renderizza e invia al motore OCR locale solo le pagine che richiedono OCR
- Ricostruisce un unico documento Markdown ordinato
- Mostra l'avanzamento pagina per pagina
- Espone una preview read-only prima del download
- Gestisce errori comuni come file non validi, PDF protetti da password, servizio OCR non disponibile, file troppo grandi o documenti con troppe pagine

## ▶️ Avvio Rapido

È richiesto Python 3.11 o successivo. Ollama non è necessario nella configurazione predefinita.

Da PowerShell, partendo dalla radice del portfolio:

```powershell
cd .\conversione-pdf-markdown-ai-coding\Script
python -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\start.ps1
```

Aprire quindi `http://127.0.0.1:8000`. Gli avvii successivi richiedono soltanto `.\start.ps1`. Per arrestare il server usare `Ctrl+C`.

Se PowerShell impedisce l'esecuzione dello script:

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

## 💼 Utilità Business

Il progetto risponde a un'esigenza concreta: rendere documenti statici e difficili da trattare nuovamente utilizzabili in processi digitali e AI-driven.

### Casi d'uso principali

- **Preparazione dati per sistemi RAG**: conversione di PDF in testo Markdown più facile da indicizzare, chunkare e interrogare.
- **Navigazione assistita da AI coding tools**: trasformazione dei PDF in file `.md` esplorabili da GitHub Copilot, Codex, Claude Code e strumenti simili, facilitando ricerca, refactoring documentale, sintesi e collegamento tra file.
- **Digitalizzazione documentale**: trasformazione di scansioni e PDF disordinati in contenuti leggibili e modificabili.
- **Automazione della documentazione**: creazione rapida di basi testuali per report, manuali, note operative, knowledge base e repository.
- **Riduzione del lavoro manuale**: eliminazione di attività ripetitive di copia, pulizia e riformattazione.
- **Workflow offline o riservati**: elaborazione locale, senza inviare documenti a servizi OCR esterni.

## 📈 Benefici Attesi

| Area | Beneficio |
|------|-----------|
| Produttività | Riduce il tempo necessario per trasformare PDF in contenuti riutilizzabili |
| Qualità del dato | Produce output più ordinato rispetto al copia-incolla manuale da PDF |
| Riservatezza | Mantiene PDF e risultati in RAM e blocca endpoint/modelli cloud per impostazione predefinita |
| Scalabilità operativa | Supporta conversione batch di più PDF nella stessa sessione |
| Integrazione AI | Prepara documenti in formato Markdown, ideale per pipeline RAG e LLM |

## 🧰 Tech Stack

`Python` · `FastAPI` · `PyMuPDF` · `RapidOCR` · `ONNX Runtime` · `Ollama opzionale` · `Vanilla HTML/CSS/JavaScript` · `Server-Sent Events`

## 🔄 Flusso Funzionale

```
PDF caricati dall'utente
        │
        ▼
Validazione file
        │
        ▼
Text layer nativo?
   ├── sì ──► estrazione diretta ─────────┐
   └── no ──► rendering ──► OCR locale ──┤
                                         ▼
                            Pulizia e assemblaggio Markdown
        │
        ▼
Preview web + download .md/.zip
```

## 👤 Ruolo

Progettazione e sviluppo end-to-end della web app: definizione requisiti, architettura backend/frontend, integrazione OCR locale, gestione asincrona dei job, progress tracking, validazione input e download dei risultati.

## 📂 Documentazione Tecnica

La documentazione tecnica del codice sorgente è disponibile in:

[Script/README.md](./Script/README.md)

> I file demo eventualmente utilizzati devono essere sintetici o pubblici. Il progetto non deve essere usato per caricare documenti riservati senza autorizzazione e adeguate misure di sicurezza; credenziali, endpoint privati e documenti aziendali non sono inclusi.
