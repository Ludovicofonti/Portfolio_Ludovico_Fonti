# 📊 Valorizzazione Impianti Pubblicitari con AI e Dati

## 📌 Contesto

Nel settore della pubblicità out-of-home (OOH), la valorizzazione degli impianti pubblicitari comunali è tradizionalmente affidata a criteri statici — posizione, dimensione, tipologia — che non tengono conto del reale potenziale espositivo di ciascun impianto. Questo approccio rende il pricing disallineato rispetto all'effettivo valore per l'inserzionista e limita la capacità dell'ente gestore di massimizzare i ricavi dalle concessioni.

Il dataset di riferimento comprende un **parco impianti significativo** georeferenziato, descritti da oltre **60 variabili candidate** (densità di punti di interesse, caratteristiche stradali, accessibilità pedonale, attributi fisici dell'impianto) e arricchiti con dati di **flusso pedonale** (dati di audience proprietari) e **flusso veicolare** (metriche di esposizione).

## 🎯 Obiettivo

Costruire uno **score di efficacia espositiva** oggettivo, misurabile e ripetibile per l'intero parco impianti, che:

- Integri tre dimensioni indipendenti: **qualità intrinseca** (componente attributi), **esposizione pedonale**, **esposizione veicolare**
- Consenta di identificare impianti sotto-valorizzati o sopra-valorizzati rispetto al costo attuale
- Supporti decisioni di pricing, rinegoziazione contratti e pianificazione campagne
- Sia trasparente e interpretabile per stakeholder non tecnici (ufficio concessioni, amministrazione comunale)

## 🏗️ Soluzione

Piattaforma **PBAi** (Piattaforma di Business Analytics per Impianti), una pipeline ML end-to-end che combina:

### Architettura a 3 componenti

| Componente | Descrizione | Approccio |
|------------|-------------|-----------|
| **Qualità Intrinseca** | Score deterministico basato su sotto-componenti pesate (categoria, dimensione, luminosità, prossimità POI) | Formula analitica con pesi predefiniti |
| **Esposizione Pedonale** | Predizione del flusso pedonale per tutti gli impianti, inclusi quelli senza dati osservati | Modello ML (Gradient Boosting) addestrato su subset di impianti con dati reali |
| **Esposizione Veicolare** | Predizione dell'opportunità di esposizione veicolare, con meccanismo di fallback per modelli a basse performance | Modello ML con fallback a metriche spaziali per area geografica |

### Pipeline operativa

```
Dataset Geospaziale → Feature Selection (stadi multipli) → Confronto Algoritmi → Training Modelli Predittivi
    → Scoring Composito → Validazione (suite automatica) → Interpretazione Multi-Metodo
```

1. **Feature Selection multi-stadio**: rimozione varianza nulla, decorrelazione, importanza per permutazione
2. **Confronto algoritmi**: validazione incrociata spaziale su algoritmi Gradient Boosting per prevenire data leakage geografico
3. **Training modelli**: predizione separata per ciascuna componente di esposizione con imputazione dove dati sono assenti
4. **Scoring composito**: aggregazione pesata con normalizzazione configurabile (relativa o assoluta)
5. **Validazione automatica**: suite di test su distribuzione, face validity, stabilità al ranking, assenza di bias geografico
6. **Interpretazione multi-metodo**: SHAP, modelli surrogati, feature importance, report Markdown

### Funzionalità chiave

- **Normalizzazione flessibile**: modalità relativa (percentile rank) per confronti interni, modalità assoluta per score stabili nel tempo
- **Calibrazione persistente**: parametri di normalizzazione salvati con versioning, auto-selezione e flag di ricalibratura
- **Interpretabilità completa**: metodi di interpretazione incrociati, aggregazione per macro-categoria, regole decisionali estraibili
- **Tracciamento esperimenti**: integrazione tracking ML con run annidati, export per stakeholder senza accesso ai sistemi tecnici
- **Cross-Validation spaziale**: validazione incrociata su griglia spaziale per prevenire data leakage geografico tra impianti vicini

## 🧰 Tech Stack

| Area | Tecnologie |
|------|-----------|
| ML & Data Science | Scikit-learn · Gradient Boosting (XGBoost, LightGBM) · Interpretabilità (SHAP, feature importance) |
| Dati geospaziali | GeoPandas · Sistemi di riferimento geospaziali (CRS) · Analisi spaziale |
| Tracking esperimenti | MLflow (backend persistente) · Versionamento parametri |
| Visualizzazione | Dashboard BI · Matplotlib · Report analitici |
| Infrastruttura | Cloud (Azure) · Python 3.x |


## 🤝 Collaborazione Cross-Funzionale

Il progetto ha richiesto una stretta collaborazione con **esperti GIS**, con competenze e strumenti differenti. Questo ha comportato:

- Allineamento su formati dati geospaziali e sistemi di riferimento (CRS)
- Traduzione di requisiti tecnici GIS in feature utilizzabili nei modelli ML
- Definizione congiunta delle variabili di densità (POI, incroci, semafori) e distanza (fermate TPL, parcheggi)
- Gestione di un flusso di lavoro condiviso tra profili tecnici eterogenei

## 📈 Impatto

| Metrica | Risultato |
|---------|----------|
| Copertura | Score calcolato per **l'intero parco impianti**, inclusi quelli senza dati di flusso diretti |
| Misurazione audience | **Metriche oggettive** di reach, esposizione e caratteristiche demografiche |
| Pricing | **Basato su analisi data-driven** (non più su criteri statici) |
| Trasparenza | Score decomponibile nelle componenti, con interpretazione multi-metodo e audit trail |
| Applicabilità | Architettura generalizzabile ad altri portfolio di asset fisici geolocalizzati |


## 👤 Ruolo

Unica risorsa Data Science sul progetto. Sviluppo autonomo di: architettura pipeline ML, modelli predittivi, sistema di scoring e normalizzazione, suite di validazione, modulo di interpretazione, dashboard analitiche. Coordinamento cross-funzionale con esperti GIS per integrazione di dati geospaziali e validazione della qualità dei dati.



---

> ⚠️ *Il dataset e i dati di input non sono inclusi per motivi di riservatezza aziendale.*
