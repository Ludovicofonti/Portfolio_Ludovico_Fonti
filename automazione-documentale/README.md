# 📄 Automazione Documentale — Scheda Commessa

## 📌 Contesto

La "Scheda Commessa" è un documento riassuntivo che raccoglie le informazioni più rilevanti da tenere a mente durante la gestione di una commessa: clausole critiche, scadenze, penali, requisiti tecnici e dati di fatturazione. La sua compilazione manuale richiedeva l'analisi di centinaia di pagine di atti complessi, un processo lungo, ripetitivo e soggetto a errore umano.

## 🎯 Obiettivo

Accelerare la compilazione della Scheda Commessa tramite un modulo AI che estragga automaticamente le informazioni rilevanti, lasciando al personale il controllo finale del documento prodotto.

## 🏗️ Soluzione

Pipeline di analisi automatica integrata con il sistema RAG aziendale:

- Processamento e confronto di **oltre 200 pagine** di documentazione complessa
- Estrazione e strutturazione automatica delle informazioni chiave nelle sezioni della scheda
- **Sezioni personalizzabili**: l'utente definisce le informazioni da estrarre e il sistema le popola automaticamente nel documento finale
- Il modulo **non sostituisce il personale**: il risultato è sempre sottoposto a un **controllo finale da parte dell'operatore**, che verifica e valida il contenuto prima dell'uso
- Integrazione nativa con il modulo RAG per accesso alla knowledge base aziendale

## 🧰 Tech Stack

`Python` · `LLM (Azure OpenAI)` · `NLP` · `Pipeline ETL` · `RAG` · `MongoDB`

## 📈 Impatto

| Metrica | Risultato |
|---------|-----------|
| Tempo di compilazione | **~5 minuti** (vs. ore di lavoro manuale) |
| Riduzione lavoro ripetitivo | **>95%** |
| Copertura | 200+ pagine per documento |

## 👤 Ruolo

Sviluppo autonomo, integrazione nativa con il modulo RAG.

---

> ⚠️ *Codice sorgente non disponibile per motivi di riservatezza aziendale.*
