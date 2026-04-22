# Documentazione Tecnica — Previsione Ricavi Apple

## Linguaggio e Librerie

| Componente | Strumento |
|---|---|
| Linguaggio | R |
| Analisi serie storiche | `tseries` (test ADF), `forecast` (ARIMA) |
| Machine learning | `caret` (cross-validation), `e1071` (SVR) |
| Visualizzazione | `corrplot` |
| Modelli surrogati | `rpart`, `rpart.plot` (albero decisionale) |

## Struttura dello Script

Lo script `analisi_previsione_ricavi_apple.R` segue un flusso che parte dalla verifica della stazionarietà fino alla previsione a 4 trimestri.

### 1. Caricamento Dati e Test di Stazionarietà

- Dataset `Ricavi_APPLE.xlsx` (foglio "Dati APPLE") contenente:
  - Ricavi trimestrali Apple
  - Fiducia Consumatori USA
  - Business Confidence USA
  - Prezzo del Rame (Copper)
- Test Augmented Dickey-Fuller su ciascuna serie.
- Le serie non stazionarie vengono **differenziate** (primo ordine).
- Post-differenziazione: verifica che tutte le serie siano stazionarie (p-value < 0.05).

### 2. Preparazione dei Dati

- Costruzione del dataframe con le serie differenziate (`ricavi_diff`, `fiducia_diff`, `copper_diff`) e `Business_Confidence_Usa` (già stazionaria).
- **Standardizzazione Z-score** di tutte le variabili (parametri salvati per la de-standardizzazione in fase di previsione).
- Split train/test: ultime 10 osservazioni riservate al test.

### 3. Support Vector Regression (SVR)

- **Kernel**: radiale (RBF)
- **Cross-validation**: time-series slicing (`initialWindow = 60`, `horizon = 10`, finestra espandibile)
- **Tuning**: grid search su C ∈ {2⁻⁵, …, 2⁵} e σ ∈ {2⁻⁵, …, 2⁵} (121 combinazioni)
- **Metriche sul test set**: MAE, RMSE, R²

### 4. Modelli Surrogati (Interpretabilità)

Poiché la SVR è un modello black-box, vengono costruiti due modelli surrogati per approssimare le predizioni e fornire interpretabilità:

| Surrogato | Metodo | Fedeltà misurata |
|---|---|---|
| Albero Decisionale | `rpart` (ANOVA, maxdepth = 30) | R² surrogato vs predizioni SVR |
| Regressione Polinomiale | `lm` con `poly(·, 2)` per ogni feature | R² surrogato vs predizioni SVR |

- L'albero decisionale produce anche un ranking di importanza delle variabili.
- Confronto visuale: grafico con valori reali, predizioni SVR e predizioni dei due surrogati.

### 5. Previsione Futura (4 Trimestri)

La previsione out-of-sample richiede valori futuri delle variabili esogene, ottenuti tramite modelli ARIMA individuali:

| Variabile | Modello ARIMA | Note |
|---|---|---|
| Fiducia Consumatori (diff) | ARIMA(1,0,1)(1,0,0)[4] | Componente stagionale trimestrale |
| Business Confidence | ARIMA(1,0,1)(0,0,1)[4] | Include dummy per la crisi 2008 (dicembre) |
| Copper (diff) | ARIMA(1,0,1)(0,0,1)[4] | — |

- Le previsioni delle esogene vengono passate alla SVR per ottenere i ricavi previsti.
- Le predizioni vengono **de-standardizzate** e riconvertite in ricavi cumulati a partire dall'ultimo valore reale.
- **Intervallo di confidenza al 95%**: calcolato come `previsione ± 1.96 × σ_residui_test` (de-standardizzato).

## File

| File | Descrizione |
|---|---|
| `analisi_previsione_ricavi_apple.R` | Script completo dell'analisi |
| `Ricavi_APPLE.xlsx` | Dataset di input (ricavi trimestrali + indicatori macro) |
