# 🍎 Previsione Trimestrale dei Ricavi Apple con Variabili Macroeconomiche

> **Progetto Universitario** · Università Politecnica delle Marche

## 📌 Contesto

Il progetto studia il legame tra i **ricavi trimestrali di Apple** e un insieme di **indicatori macroeconomici esterni** (Q4 1990 – Q4 2021), con l'obiettivo di formulare una previsione per il **primo trimestre 2022**. L'approccio integra modelli statistici (ARIMA) e machine learning (Support Vector Regression) per catturare relazioni non lineari tra variabili esogene e performance aziendale.

## 🏗️ Pipeline di Analisi

### 1. Variabili Macroeconomiche Analizzate
- **Fiducia dei consumatori USA** — indicatore instabile, con forte declino post-2007 e durante il COVID-19
- **Fiducia delle imprese USA** — più stabile, con lieve flessione nel lungo periodo
- **Prezzo del rame (Copper)** — variabile ciclica e volatile, legata alla domanda di componenti elettronici
- **PCE (Personal Consumption Expenditures)** — crescita costante, indicatore di domanda strutturale solida
- **IT Investment** — investimenti in tecnologia, rallentamento post-2015 per possibile maturazione del settore

### 2. Preprocessing delle Serie Temporali
- Trasformazione in **logaritmi naturali** per stabilizzare la varianza
- **Differenziazione** per soddisfare le condizioni di stazionarietà richieste da ARIMA

### 3. Modelli ARIMA per le Variabili Esogene
Previsione di ciascuna variabile macroeconomica per alimentare il modello SVR:

| Variabile | Modello ARIMA |
|-----------|--------------|
| Copper | ARIMA(0,1,0) |
| PCE | ARIMA(1,1,0) |
| IT Investment | ARIMA(0,1,0) |
| Business Confidence | ARIMA(0,1,0) + dummy Q4-2008 |
| Consumer Confidence | ARIMA(1,1,0) |

### 4. Modello Predittivo — Support Vector Regression (SVR)
- **Kernel radiale (RBF)** per catturare pattern complessi e non lineari
- Split train/test: **80% / 20%**, validazione incrociata a **5 fold**, tuning automatico dei parametri
- **Albero decisionale come modello surrogato** per l'interpretabilità del modello SVR (black box → white box)

## 🔍 Importanza delle Variabili (dal modello surrogato)

| Variabile | Ruolo nel modello |
|-----------|------------------|
| **Copper** (prezzo rame) | **Driver principale** — rame elevato → ricavi più alti; usato nei componenti tech, sensibile ai cicli economici |
| **IT Investment** | Impatto positivo quando gli investimenti sono elevati |
| **PCE** | Influenza moderata; se molto bassa penalizza le previsioni anche con buoni IT Investment |
| **Business & Consumer Confidence** | Peso minore, ma rilevante in combinazione: entrambi bassi → previsioni peggiori |

## 📊 Previsione Q1 2022

| Metrica | Valore |
|---------|--------|
| **Ricavi stimati** | **97.520** |
| Intervallo di confidenza 95% | 97.520 – 105.752 |
| RMSE | 6.424,33 |

Il modello indica una **crescita stabile e moderata**, confermando la resilienza del business Apple in un contesto macroeconomico incerto, probabilmente sostenuta dalla fedeltà della clientela e dalla domanda strutturale di prodotti tech.

## 🧰 Tech Stack

`R` · `ARIMA` · `Support Vector Regression (SVR)` · `Albero Decisionale (surrogato)` · `Trasformazione Logaritmica` · `Cross-Validation`

## 🏷️ Tags

`Time Series` · `Forecasting` · `SVR` · `ARIMA` · `Variabili Macroeconomiche` · `Apple` · `Finance`
