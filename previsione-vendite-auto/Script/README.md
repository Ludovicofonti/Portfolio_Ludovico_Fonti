# Documentazione Tecnica — Previsione Vendite Auto USA

## Linguaggio e Librerie

| Componente | Strumento |
|---|---|
| Linguaggio | R |
| Serie storiche | `forecast` (ARIMA, ARIMAX), `tseries` (ADF), `urca` (KPSS) |
| Test statistici | `lmtest` (Granger, Wald, Ljung-Box) |
| Visualizzazione | `ggplot2`, `zoo` |
| Manipolazione dati | `dplyr` |
| Performance | `tictoc` (timing grid search) |

## Struttura dello Script

Lo script `analisi_previsione_vendite_auto.R` è organizzato in due fasi (univariata e multivariata), con analisi aggiuntive sugli shock storici.

### 1. Caricamento e Preparazione Dati

- Dataset `dati_vendite_auto.xlsx` con colonne: `Date`, `Value` (vendite auto), `petrol_price`, `unemp_rate`, `interest`.
- Parsing date in formato `"Jan-1992"` tramite `as.yearmon`.
- Separazione automatica dei periodi futuri (righe con `Value = NA`).
- Serie storica: **gennaio 1992 – dicembre 2024** (frequenza mensile).

### 2. Analisi Esplorativa (EDA)

- **Serie storica originale**: visualizzazione del trend con annotazione degli eventi principali (crisi 2008, COVID-19, ripresa post-2021).
- **Scomposizione STL** (Seasonal-Trend-Loess): separazione in trend, stagionalità e residuo.
- **Varianza spiegata**: calcolo della percentuale di varianza attribuita a ciascuna componente.

### 3. Test di Stazionarietà

| Test | Serie originale | Serie differenziata |
|---|---|---|
| ADF (Augmented Dickey-Fuller) | Non stazionaria | Stazionaria |
| KPSS | Conferma non stazionarietà | — |

---

## Fase 1: Modello Univariato — ARIMA

- **Split**: train fino a novembre 2024, test = dicembre 2024.
- **Selezione modello**: `auto.arima` con ricerca esaustiva (`stepwise = FALSE`, `approximation = FALSE`).
- **Diagnostica residui**:
  - `checkresiduals` (ACF, istogramma, Ljung-Box)
  - Test Ljung-Box (lag = 12): verifica assenza di autocorrelazione
  - Test di Wald (`coeftest`): significatività dei coefficienti

---

## Selezione Variabili Esogene — Test di Granger

- Tutte le serie vengono differenziate (requisito di stazionarietà).
- Test di causalità di Granger (ordine = 7) per ciascuna variabile esogena:

| Variabile | H₀ |
|---|---|
| Prezzo petrolio | Non causa le vendite |
| Tasso di disoccupazione | Non causa le vendite |
| Tasso d'interesse | Non causa le vendite |

---

## Fase 2: Modello Multivariato — ARIMAX

### Preparazione

- **Trasformazione logaritmica** di tutte le variabili per stabilizzare la varianza.
- Rimozione valori non finiti (log di zero).

### Grid Search

- Ricerca esaustiva sugli ordini:
  - p ∈ {0, 1, 2, 3}, d = 1, q ∈ {0, 1, 2, 3}
  - P ∈ {0, 1}, D = 1, Q ∈ {0, 1}, periodo = 12
- Criterio di selezione: **RMSE minimo** sul training set.
- Totale combinazioni valutate: 4 × 4 × 2 × 2 = 64.

### Diagnostica

- Ljung-Box (lag = 12) sui residui
- Test di Shapiro-Wilk per la normalità dei residui

---

## Analisi degli Shock Storici

Quattro variabili dummy vengono aggiunte al modello ARIMAX per quantificare l'impatto di shock macro:

| Shock | Periodo |
|---|---|
| Dot-com + 11 settembre | Giugno 2001 – Dicembre 2002 |
| Crisi finanziaria | Giugno 2008 – Dicembre 2009 |
| COVID-19 | Febbraio 2020 – Luglio 2020 |
| Inflazione e tassi alti | Gennaio 2022 – Gennaio 2023 |

Il coefficiente di ciascuna dummy (in scala log) misura la direzione e l'entità dell'impatto.

---

## Previsione Q1 2025

- **Scenario base**: valori attesi delle variabili esogene per gennaio–marzo 2025 inseriti manualmente (petrolio, disoccupazione, tasso d'interesse).
- **Intervalli di confidenza**:
  - IC parametrici all'80% e 95% (dal forecast ARIMAX)
  - IC basati sui quantili dei residui (1%–99%, 25%–75%)
- Ritrasformazione dalla scala log alla scala originale tramite `exp()`.

## File

| File | Descrizione |
|---|---|
| `analisi_previsione_vendite_auto.R` | Script completo dell'analisi |
| `dati_vendite_auto.xlsx` | Dataset principale (vendite + variabili macro) |
| `FEDFUNDS(tassi interesse).csv` | Serie storica dei tassi d'interesse (fonte: FRED) |
| `UNRATE(tasso di disoccupazione).csv` | Serie storica del tasso di disoccupazione (fonte: FRED) |
