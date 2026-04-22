# Documentazione Tecnica — Redditività Investimenti nel Settore Media

## Linguaggio e Librerie

| Componente | Strumento |
|---|---|
| Linguaggio | R |
| Manipolazione dati | `dplyr`, `readxl` |
| Visualizzazione | `ggplot2`, `GGally`, `corrplot` |
| Outlier detection | `isotree` (Isolation Forest) |
| Modellazione | `lm` (regressione lineare), `caret` (cross-validation) |
| Diagnostica | `car` (VIF), `lmtest` (Breusch-Pagan), `olsrr` (test normalità) |
| Inferenza | `boot` (bootstrap) |

## Struttura dello Script

Lo script `analisi_redditivita_media.R` stima l'EPS (Earnings Per Share) a 12 mesi per aziende del Russell 3000, applicando poi il modello a un campione di aziende italiane del settore media.

### 1. Caricamento Dati

- **Training set**: `Russell_3000_Fundamentals_Enlarged_With_README.xlsx` (due fogli: dataset features e target), uniti tramite `left_join` su `Record ID`.
- **Test set**: `Dati_Sintetici_Settore_Media.csv` con fondamentali di aziende italiane del settore media.
- Rinomina delle variabili: `RETURN_ON_ EQUITY` → `ROE`, `RETURN_ON_ASSET` → `ROA`, `RETURN_ON_INVESTED_CAPITAl` → `ROIC`.

### 2. Analisi Esplorativa (EDA)

- Istogrammi delle variabili chiave: `EPS_12M_FORWARD`, `FREE_CASH_FLOW`, `ENTERPRISE_VALUE`, `NET_SALES`, `EBITDA`, `ROE`, `ROA`.
- Boxplot per individuare la dispersione e gli outlier.
- Scatterplot delle variabili vs EPS con linea di regressione.
- Boxplot di EBITDA per settore industriale (`INDUSTRY`).
- Matrice di correlazione sui dati grezzi.

### 3. Rimozione Outlier — Isolation Forest

- `ntrees = 100`, soglia al **88° percentile** (rimozione del ~12% delle osservazioni più anomale).
- Visualizzazione della distribuzione degli anomaly score con soglia evidenziata.

### 4. Feature Engineering

- **Standardizzazione Z-score** delle variabili indipendenti (la target `EPS_12M_FORWARD` viene preservata nella scala originale).
- **Trasformazione logaritmica** con `signed_log(x) = sign(x) · log1p(|x|)` per gestire distribuzioni asimmetriche e valori negativi. Applicata a: `EPS`, `FREE_CASH_FLOW`, `ENTERPRISE_VALUE`, `NET_SALES`, `EBITDA`.

### 5. Analisi Multicollinearità

- Matrice di correlazione post-preprocessing.
- Calcolo degli **autovalori** e del **Condition Number** della matrice di correlazione.
- Confronto con e senza `ROIC` (ridondante con `ROA`): `ROIC` viene esclusa dal modello.

### 6. Regressione Lineare Multipla

- **Target**: `log_EPS_12M_FORWARD`
- **Features**: `log_NET_SALES`, `log_FREE_CASH_FLOW`, `ROE`, `ROA`, `log_EBITDA`, `log_ENTERPRISE_VALUE`
- **VIF** calcolato per verificare la multicollinearità residua.

### 7. Diagnostica del Modello

| Test | Obiettivo |
|---|---|
| Grafici diagnostici (4 panel) | Residui vs Fitted, Q-Q plot, Scale-Location, Leverage |
| Test t | Media dei residui = 0 |
| Shapiro-Wilk | Normalità dei residui |
| Kolmogorov-Smirnov, Cramér-von Mises, Anderson-Darling | Normalità (batteria `ols_test_normality`) |
| Breusch-Pagan | Omoschedasticità |
| Residui standardizzati e studentizzati (jackknife) | Identificazione outlier residuali con correzione di Bonferroni |

### 8. Bootstrap — Intervalli di Confidenza

- 1.000 campioni bootstrap per stimare gli intervalli di confidenza al 95% dei coefficienti (metodo percentile).
- Confronto con gli standard error parametrici del modello OLS.

### 9. Cross-Validation (K-Fold)

- 10-fold cross-validation tramite `caret::train` con metodo `"lm"`.
- Metriche riportate: RMSE, R², MAE su ogni fold.

### 10. Previsione Aziende Italiane

- Preprocessing identico al training (Z-score + signed_log).
- Previsione in scala log, poi ritrasformazione: `EPS_previsto = exp(pred) - 1`.
- Tabella comparativa: EPS reale vs previsto con errore percentuale.
- Grafico a barre affiancate per il confronto visuale.

## File

| File | Descrizione |
|---|---|
| `analisi_redditivita_media.R` | Script completo dell'analisi |
| `Russell_3000_Fundamentals_Enlarged_With_README.xlsx` | Dataset Russell 3000 (training) |
| `Dati_Sintetici_Settore_Media.csv` | Dataset aziende italiane del settore media (test) |
