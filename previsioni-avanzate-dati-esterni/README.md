# 📈 Previsioni Avanzate con Integrazione di Dati Esterni

> **SYEEW SRL** · 2024 – 2025

## 📌 Contesto

I modelli predittivi esistenti si basavano esclusivamente su dati storici interni (vendite passate, stagionalità), ignorando completamente i fattori esterni che influenzano le performance commerciali. Il risultato erano previsioni fragili di fronte a qualsiasi evento contestuale non catturato dai dati interni.

> **Esempio concreto:** un ristorante sul lungomare vede le proprie performance crollare in una giornata di pioggia. Un modello che guarda solo le serie storiche di fatturato non può anticipare questo calo — ma un modello che integra le previsioni meteo sì.

I clienti operavano in settori dove le performance erano sistematicamente condizionate da variabili esterne — meteo, inflazione, indici di fiducia dei consumatori — che i modelli basati sui soli dati interni non riuscivano a catturare. Le previsioni risultavano quindi inaccurate proprio nei momenti di maggiore variabilità, quando servivano di più.

## 🎯 Obiettivo

Migliorare l'accuratezza e la robustezza dei modelli predittivi integrando sistematicamente **variabili esogene** (meteo, indicatori macroeconomici, festività), rendendo le previsioni affidabili anche in presenza di fattori di contesto non visibili dai soli dati di vendita.

## 🏗️ Soluzione

Pipeline end-to-end di forecasting multi-variato che unifica tre fonti dati in un unico modello predittivo:

- **Data Integration** — merge automatizzato di dati di vendita, dati meteo giornalieri (temperatura, precipitazioni, umidità) e indicatori macroeconomici mensili (indice di fiducia consumatori, indice dei prezzi)
- **Feature Engineering** — arricchimento temporale con encoding ciclico (mese, trimestre, giorno della settimana) e calendario festività italiane come covariate
- **Modello Custom TSMixer** — architettura MLP-Mixer adattata alle serie temporali, con attivazione Mish per un gradient flow più stabile e **regressione quantilica** per output probabilistici (intervalli di confidenza, non solo previsioni puntuali)
- **Previsioni multi-gruppo** — forecasting simultaneo su più entità (punti vendita × categorie prodotto), con covariate statiche e dinamiche
- **Hyperparameter Tuning** — ottimizzazione multi-obiettivo (RMSE + MAE) con Optuna e sampler NSGA-III

## 🧰 Tech Stack

`Python` · `Darts` · `PyTorch` · `PyTorch Lightning` · `Optuna` · `Scikit-Learn` · `API REST` · `Time Series Analysis`

## 📈 Impatto

| Metrica | Risultato |
|---------|-----------|
| Accuratezza modelli predittivi | **+23%** rispetto al modello senza variabili esogene |
| Robustezza previsioni | Significativamente migliorate su fattori di mercato e stagionalità anomale |
| Copertura | Multi-settore: ristorazione, retail, servizi |
| Output | Previsioni probabilistiche con intervalli di confidenza |

## 👤 Ruolo

Unica risorsa Data Science sul progetto. Progettazione dell'architettura predittiva, integrazione variabili esogene, sviluppo modello custom, feature engineering e ottimizzazione iperparametri.

---

> 📂 *Il codice sorgente e i dataset (anonimizzati) sono disponibili nella cartella [`Script/`](Script/). Consultare il [README tecnico](Script/README.md) per i dettagli implementativi.*
