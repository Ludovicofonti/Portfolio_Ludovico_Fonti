# 🍎 Previsione Trimestrale dei Ricavi Apple con Variabili Macroeconomiche

> **Progetto Universitario** · Università Politecnica delle Marche

## 📌 Contesto

Il progetto analizza la relazione tra i **ricavi trimestrali di Apple** e tre indicatori macroeconomici: fiducia dei consumatori USA, fiducia delle imprese USA e prezzo del rame. L'obiettivo è valutare un modello di Support Vector Regression su una finestra temporale di test e produrre una previsione dei ricavi per i quattro trimestri successivi alle osservazioni contenute nel dataset.

## 🎯 Obiettivo

- Preparare serie trimestrali stazionarie e confrontabili.
- Stimare le variazioni dei ricavi con una **Support Vector Regression (SVR)** a kernel radiale.
- Valutare il modello sulle ultime 10 osservazioni disponibili.
- Approssimare la SVR con modelli surrogati più interpretabili.
- Generare previsioni a quattro trimestri usando stime ARIMA delle variabili esogene.

## 🏗️ Pipeline di analisi

### 1. Dati utilizzati

Il file `Script/Ricavi_APPLE.xlsx`, foglio `Dati APPLE`, contiene:

- ricavi trimestrali Apple;
- fiducia dei consumatori USA;
- fiducia delle imprese USA;
- prezzo del rame (`Copper`).

### 2. Preprocessing delle serie temporali

- Test Augmented Dickey-Fuller per verificare la stazionarietà.
- Differenziazione al primo ordine di ricavi, fiducia dei consumatori e rame.
- Mantenimento della fiducia delle imprese in livello, poiché trattata come già stazionaria.
- Standardizzazione Z-score con conservazione dei parametri necessari alla successiva trasformazione inversa.
- Suddivisione temporale: le ultime 10 osservazioni formano il test set.

### 3. Modello predittivo SVR

- Kernel radiale RBF.
- Cross-validation per serie temporali con `initialWindow = 60`, `horizon = 10` e finestra espandibile.
- Grid search su 121 combinazioni di `C` e `sigma`, entrambe nell'intervallo da 2⁻⁵ a 2⁵.
- Valutazione sul test set tramite MAE, RMSE e R².

### 4. Interpretabilità

Le predizioni della SVR vengono approssimate con due modelli surrogati:

- albero decisionale `rpart`, con ranking dell'importanza delle variabili;
- regressione polinomiale di secondo grado.

La fedeltà dei surrogati è misurata confrontando le loro predizioni con quelle della SVR tramite R².

### 5. Previsione dei quattro trimestri successivi

Le variabili esogene future vengono stimate separatamente:

| Variabile | Modello ARIMA | Note |
|---|---|---|
| Fiducia consumatori differenziata | ARIMA(1,0,1)(1,0,0)[4] | Stagionalità trimestrale |
| Fiducia imprese | ARIMA(1,0,1)(0,0,1)[4] | Dummy per dicembre 2008 |
| Rame differenziato | ARIMA(1,0,1)(0,0,1)[4] | Stagionalità trimestrale |

Le stime vengono passate alla SVR, trasformate nuovamente nella scala originale e cumulate a partire dall'ultimo ricavo osservato.

## 📊 Output

Lo script calcola a runtime:

- MAE, RMSE e R² sul test set;
- R² di fedeltà dei due modelli surrogati;
- confronto grafico tra valori reali, SVR e surrogati;
- tabella delle previsioni dei ricavi per quattro trimestri, con intervallo di confidenza al 95%.

I valori numerici non sono riportati in modo statico nel README: dipendono dall'esecuzione sul dataset e dalla versione delle dipendenze installate.

## 🧰 Tech Stack

`R` · `forecast` · `caret` · `e1071` · `SVR` · `ARIMA` · `rpart` · `Time-Series Cross-Validation`

## 📁 Struttura

| Percorso | Contenuto |
|---|---|
| `Script/analisi_previsione_ricavi_apple.R` | Pipeline completa di analisi e previsione |
| `Script/Ricavi_APPLE.xlsx` | Dataset di input |
| [`Script/README.md`](./Script/README.md) | Documentazione tecnica dettagliata |

## 🏷️ Tags

`Time Series` · `Forecasting` · `SVR` · `ARIMA` · `Variabili Macroeconomiche` · `Apple` · `Finance`

> Progetto didattico basato su dati finanziari e macroeconomici. Le analisi non costituiscono consulenza finanziaria o raccomandazione di investimento; per ogni riuso degli input vanno verificate fonte, licenza e condizioni d'uso.
