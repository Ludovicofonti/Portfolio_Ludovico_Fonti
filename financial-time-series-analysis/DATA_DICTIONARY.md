# Data Dictionary — Financial Time Series Platform

Descrive tutte le tabelle presenti in `data/finance.duckdb`, i loro campi, i tipi, il significato e le statistiche di copertura.

---

## Database: `data/finance.duckdb`

| Schema        | Tipo       | Descrizione                                             |
|---------------|------------|---------------------------------------------------------|
| `raw_finance` | Sorgente   | Dati grezzi ingeriti da dlt (Yahoo Finance / FRED)      |
| `analytics`   | Elaborati  | Dati trasformati da dbt (staging → intermediate → mart) |

---

## Schema `raw_finance`

### Tabelle di prezzo (`prices_*`)

Struttura identica per tutte le sei tabelle di prezzo. Ogni riga rappresenta una giornata di negoziazione per un singolo strumento.

| Campo         | Tipo      | Descrizione                                                               |
|---------------|-----------|---------------------------------------------------------------------------|
| `symbol`      | VARCHAR   | Ticker Yahoo Finance (es. `AAPL`, `BTC-USD`, `^GSPC`)                    |
| `asset_class` | VARCHAR   | Classe di appartenenza: `stocks`, `crypto`, `forex`, `commodities`, `indices`, `bonds` |
| `date`        | DATE      | Data di negoziazione (chiave primaria insieme a `symbol`)                 |
| `open`        | DOUBLE    | Prezzo di apertura della sessione                                         |
| `high`        | DOUBLE    | Massimo intraday                                                          |
| `low`         | DOUBLE    | Minimo intraday                                                           |
| `close`       | DOUBLE    | Prezzo di chiusura (adjusted per split e dividendi tramite `auto_adjust`) |
| `volume`      | DOUBLE    | Volumi scambiati. Per forex, bond e VIX è convenzionalmente 0.0          |
| `_dlt_load_id`| VARCHAR   | ID del batch di caricamento dlt (tracciabilità)                           |
| `_dlt_id`     | VARCHAR   | ID univoco di riga generato da dlt                                        |

#### Copertura per asset class

| Tabella               | Simboli                          | Periodo                      | Righe  |
|-----------------------|----------------------------------|------------------------------|--------|
| `prices_stocks`       | AAPL, MSFT, TSLA                 | 2018-01-02 → 2026-05-27      | 6 333  |
| `prices_crypto`       | BTC-USD, ETH-USD                 | 2018-01-01 → 2026-05-27      | 6 138  |
| `prices_forex`        | EURUSD=X, GBPUSD=X               | 2018-01-01 → 2026-05-27      | 4 374  |
| `prices_commodities`  | GC=F (oro), CL=F (petrolio WTI)  | 2018-01-02 → 2026-05-27      | 4 225  |
| `prices_indices`      | ^GSPC (S&P500), ^DJI, ^VIX       | 2018-01-02 → 2026-05-27      | 6 334  |
| `prices_bonds`        | ^TNX (10Y yield), ^TYX (30Y yield)| 2018-01-02 → 2026-05-27     | 4 222  |

> **Nota sulle unità**: i prezzi sono in USD (o nella valuta base per il forex). I rendimenti dei bond (^TNX, ^TYX) sono espressi in punti percentuali, non in prezzi assoluti — il campo `close` vale es. `4.25` per un yield del 4.25%.

---

### Tabelle di sistema dlt (non usare direttamente)

| Tabella               | Descrizione                                              |
|-----------------------|----------------------------------------------------------|
| `_dlt_loads`          | Registro dei batch di caricamento completati             |
| `_dlt_pipeline_state` | Stato interno della pipeline (checkpoint, versioni)      |
| `_dlt_version`        | Versione dello schema dlt e hash di validazione          |

---

## Schema `analytics`

### `stg_prices` (VIEW)

Union di tutte e sei le tabelle `raw_finance.prices_*`. Punto di ingresso unico per le trasformazioni dbt successive.

| Campo         | Tipo    | Fonte            | Descrizione                          |
|---------------|---------|------------------|--------------------------------------|
| `symbol`      | VARCHAR | raw_finance.*    | Ticker dello strumento               |
| `asset_class` | VARCHAR | raw_finance.*    | Classe dell'asset                    |
| `date`        | DATE    | raw_finance.*    | Data di negoziazione                 |
| `open`        | DOUBLE  | raw_finance.*    | Prezzo di apertura                   |
| `high`        | DOUBLE  | raw_finance.*    | Massimo di giornata                  |
| `low`         | DOUBLE  | raw_finance.*    | Minimo di giornata                   |
| `close`       | DOUBLE  | raw_finance.*    | Prezzo di chiusura adjusted          |
| `volume`      | DOUBLE  | raw_finance.*    | Volumi                               |

**Righe totali**: ~31 626 (tutte le asset class combinate)

---

### `stg_macro` (VIEW)

Dati macroeconomici FRED. Attualmente **stub vuoto** (0 righe): richiede la variabile ambiente `FRED_API_KEY` e l'attivazione in `config/data_sources.yml`.

| Campo        | Tipo    | Descrizione                                      |
|--------------|---------|--------------------------------------------------|
| `series_id`  | VARCHAR | Codice FRED (es. `GDPC1`, `CPIAUCSL`, `FEDFUNDS`) |
| `description`| VARCHAR | Nome esteso della serie (es. "Real GDP")          |
| `date`       | DATE    | Data di riferimento del dato                     |
| `value`      | DOUBLE  | Valore della serie (unità dipendono dalla serie)  |

**Serie FRED previste** (quando l'API key sarà configurata):

| Series ID   | Descrizione                     | Frequenza  | Unità         |
|-------------|---------------------------------|------------|---------------|
| GDPC1       | Real GDP                        | Trimestrale | Miliardi USD  |
| CPIAUCSL    | CPI All Items                   | Mensile    | Indice (1982=100) |
| T10YIE      | 10Y Breakeven Inflation         | Giornaliera| % annualizzata|
| FEDFUNDS    | Federal Funds Rate (target)     | Mensile    | % annualizzata|
| DFF         | Federal Funds Rate (effettivo)  | Giornaliera| % annualizzata|
| DGS2        | 2Y Treasury Yield               | Giornaliera| % annualizzata|
| DGS5        | 5Y Treasury Yield               | Giornaliera| % annualizzata|
| DGS10       | 10Y Treasury Yield              | Giornaliera| % annualizzata|
| DGS30       | 30Y Treasury Yield              | Giornaliera| % annualizzata|
| T10Y2Y      | Spread 10Y - 2Y (curva dei tassi)| Giornaliera| punti %      |
| T10Y3M      | Spread 10Y - 3M                 | Giornaliera| punti %       |
| UNRATE      | Tasso di disoccupazione         | Mensile    | %             |
| VIXCLS      | CBOE VIX (chiusura)             | Giornaliera| punti (volatilità implicita) |
| DCOILWTICO  | WTI Crude Oil Price             | Giornaliera| USD/barile    |

---

### `int_daily_returns` (TABLE)

Rendimenti giornalieri calcolati da `stg_prices`. Tabella intermedia — non destinata al consumo diretto.

| Campo             | Tipo    | Formula / Fonte                                    | Descrizione                                        |
|-------------------|---------|----------------------------------------------------|----------------------------------------------------|
| `symbol`          | VARCHAR | stg_prices                                         | Ticker                                             |
| `asset_class`     | VARCHAR | stg_prices                                         | Classe dell'asset                                  |
| `date`            | DATE    | stg_prices                                         | Data                                               |
| `close`           | DOUBLE  | stg_prices                                         | Prezzo di chiusura                                 |
| `log_return`      | DOUBLE  | $\ln(P_t / P_{t-1})$                              | Rendimento logaritmico giornaliero                 |
| `ma_20`           | DOUBLE  | AVG(close) OVER 20 giorni                          | Media mobile 20 giorni del prezzo                  |
| `ma_60`           | DOUBLE  | AVG(close) OVER 60 giorni                          | Media mobile 60 giorni del prezzo                  |
| `rolling_vol_20`  | DOUBLE  | STDDEV(log_return) OVER 20 giorni                  | Volatilità storica a 20 giorni (non annualizzata)  |
| `rolling_vol_60`  | DOUBLE  | STDDEV(log_return) OVER 60 giorni                  | Volatilità storica a 60 giorni (non annualizzata)  |
| `cumulative_return`| DOUBLE | $\sum \ln(P_t / P_{t-1})$ da inizio serie          | Rendimento cumulativo logaritmico                  |

**Righe**: ~31 610

---

### `int_lagged_features` (TABLE)

Feature engineering con lag dei rendimenti. Usata come input per modelli ML e per ARIMA/SARIMA con esogene.

| Campo             | Tipo    | Formula / Fonte                  | Descrizione                                         |
|-------------------|---------|----------------------------------|-----------------------------------------------------|
| `symbol`          | VARCHAR | int_daily_returns                | Ticker                                              |
| `asset_class`     | VARCHAR | int_daily_returns                | Classe dell'asset                                   |
| `date`            | DATE    | int_daily_returns                | Data                                                |
| `close`           | DOUBLE  | int_daily_returns                | Prezzo di chiusura                                  |
| `log_return`      | DOUBLE  | int_daily_returns                | Rendimento logaritmico giornaliero                  |
| `ma_20`           | DOUBLE  | int_daily_returns                | Media mobile 20 giorni                              |
| `ma_60`           | DOUBLE  | int_daily_returns                | Media mobile 60 giorni                              |
| `rolling_vol_20`  | DOUBLE  | int_daily_returns                | Volatilità rolling 20 giorni                        |
| `rolling_vol_60`  | DOUBLE  | int_daily_returns                | Volatilità rolling 60 giorni                        |
| `lag_1`           | DOUBLE  | LAG(log_return, 1)               | Rendimento del giorno precedente                    |
| `lag_2`           | DOUBLE  | LAG(log_return, 2)               | Rendimento di 2 giorni fa                           |
| `lag_3`           | DOUBLE  | LAG(log_return, 3)               | Rendimento di 3 giorni fa                           |
| `lag_4`           | DOUBLE  | LAG(log_return, 4)               | Rendimento di 4 giorni fa                           |
| `lag_5`           | DOUBLE  | LAG(log_return, 5)               | Rendimento di 5 giorni fa (settimana lavorativa)    |
| `squared_return`  | DOUBLE  | log_return²                      | Proxy della varianza (correlata alla volatilità)    |
| `direction_up`    | INTEGER | SIGN(log_return) > 0 → 1, else 0 | Target binario: 1 se il rendimento è positivo       |

**Righe**: ~31 610

---

### `fct_asset_returns` (TABLE)

Tabella mart principale. Combinazione di `int_daily_returns` e `int_lagged_features` con tutte le feature necessarie all'analisi e ai modelli.

| Campo             | Tipo    | Descrizione                                                              |
|-------------------|---------|--------------------------------------------------------------------------|
| `symbol`          | VARCHAR | Ticker dello strumento                                                   |
| `asset_class`     | VARCHAR | Classe dell'asset                                                        |
| `date`            | DATE    | Data di negoziazione                                                     |
| `close`           | DOUBLE  | Prezzo di chiusura adjusted                                              |
| `log_return`      | DOUBLE  | Rendimento logaritmico: $r_t = \ln(P_t / P_{t-1})$                     |
| `squared_return`  | DOUBLE  | $r_t^2$ — proxy della varianza condizionale                             |
| `direction_up`    | INTEGER | 1 se $r_t > 0$, altrimenti 0                                            |
| `ma_20`           | DOUBLE  | Media mobile 20 giorni del prezzo di chiusura                            |
| `ma_60`           | DOUBLE  | Media mobile 60 giorni del prezzo di chiusura                            |
| `rolling_vol_20`  | DOUBLE  | Deviazione standard dei rendimenti su 20 giorni (non annualizzata)       |
| `rolling_vol_60`  | DOUBLE  | Deviazione standard dei rendimenti su 60 giorni (non annualizzata)       |
| `lag_1` … `lag_5` | DOUBLE | Rendimenti logaritmici dei giorni precedenti (1–5)                       |

**Righe**: ~31 540 | **Copertura**: 2018-01-10 → 2026-05-27 (le prime righe vengono perse per il calcolo dei lag)

#### Copertura per strumento

| Simbolo    | Classe      | Osservazioni | Periodo                    |
|------------|-------------|--------------|----------------------------|
| AAPL       | stocks      | 2 110        | 2018-01-03 → 2026-05-27    |
| MSFT       | stocks      | 2 110        | 2018-01-03 → 2026-05-27    |
| TSLA       | stocks      | 2 110        | 2018-01-03 → 2026-05-27    |
| BTC-USD    | crypto      | 3 068        | 2018-01-02 → 2026-05-27    |
| ETH-USD    | crypto      | 3 068        | 2018-01-02 → 2026-05-27    |
| EURUSD=X   | forex       | 2 186        | 2018-01-02 → 2026-05-27    |
| GBPUSD=X   | forex       | 2 186        | 2018-01-02 → 2026-05-27    |
| GC=F       | commodities | 2 111        | 2018-01-03 → 2026-05-27    |
| CL=F       | commodities | 2 110        | 2018-01-03 → 2026-05-27    |
| ^GSPC      | indices     | 2 110        | 2018-01-03 → 2026-05-27    |
| ^DJI       | indices     | 2 110        | 2018-01-03 → 2026-05-27    |
| ^VIX       | indices     | 2 111        | 2018-01-03 → 2026-05-27    |
| ^TNX       | bonds       | 2 110        | 2018-01-03 → 2026-05-27    |
| ^TYX       | bonds       | 2 110        | 2018-01-03 → 2026-05-27    |

---

### `fct_risk_metrics` (TABLE)

Metriche di rischio aggregate per strumento, calcolate sull'intero storico disponibile. Una riga per simbolo.

| Campo                    | Tipo   | Formula                                                          | Descrizione                                           |
|--------------------------|--------|------------------------------------------------------------------|-------------------------------------------------------|
| `symbol`                 | VARCHAR|                                                                  | Ticker dello strumento                                |
| `asset_class`            | VARCHAR|                                                                  | Classe dell'asset                                     |
| `first_date`             | DATE   | MIN(date)                                                        | Prima osservazione disponibile                        |
| `last_date`              | DATE   | MAX(date)                                                        | Ultima osservazione disponibile                       |
| `n_obs`                  | BIGINT | COUNT(*)                                                         | Numero di osservazioni                                |
| `expected_annual_return_pct` | DOUBLE | $\bar{r} \times 252 \times 100$                           | Rendimento atteso annualizzato in percentuale         |
| `vol_annual_pct`         | DOUBLE | $\sigma_r \times \sqrt{252} \times 100$                         | Volatilità annualizzata in percentuale                |
| `sharpe_ratio`           | DOUBLE | $\text{return} / \text{vol}$ (risk-free = 0)                    | Sharpe ratio (senza risk-free rate)                   |
| `var_95_daily_pct`       | DOUBLE | 5° percentile di $r_t \times 100$                               | VaR giornaliero al 95% in punti percentuali           |
| `cvar_95_daily_pct`      | DOUBLE | $\mathbb{E}[r_t \mid r_t \leq \text{VaR}_{95}] \times 100$     | CVaR (Expected Shortfall) al 95% in punti percentuali |

#### Dati correnti (aggiornati al 27 maggio 2026)

| Simbolo    | Classe      | Rend. Annuo | Vol. Annua | Sharpe | VaR 95% | CVaR 95% |
|------------|-------------|-------------|------------|--------|---------|----------|
| TSLA       | stocks      | +36.14%     | 62.50%     | 0.578  | -5.80%  | -8.97%   |
| AAPL       | stocks      | +24.41%     | 30.47%     | 0.801  | -3.02%  | -4.47%   |
| MSFT       | stocks      | +19.79%     | 28.51%     | 0.694  | -2.82%  | -4.14%   |
| BTC-USD    | crypto      | +13.92%     | 53.86%     | 0.258  | -5.18%  | -8.20%   |
| ETH-USD    | crypto      | +7.90%      | 70.73%     | 0.112  | -6.91%  | -10.86%  |
| GC=F       | commodities | +14.56%     | 17.21%     | 0.846  | -1.68%  | -2.60%   |
| CL=F       | commodities | +11.78%     | 48.23%     | 0.244  | -4.05%  | -7.11%   |
| ^GSPC      | indices     | +12.25%     | 19.41%     | 0.631  | -1.80%  | -2.99%   |
| ^DJI       | indices     | +8.52%      | 18.94%     | 0.450  | -1.70%  | -2.88%   |
| ^VIX       | indices     | +6.10%      | 129.31%    | 0.047  | -11.06% | -15.46%  |
| EURUSD=X   | forex       | -0.36%      | 7.17%      | -0.050 | -0.72%  | -0.98%   |
| GBPUSD=X   | forex       | -0.05%      | 8.68%      | -0.006 | -0.86%  | -1.23%   |
| ^TNX       | bonds       | +7.14%      | 49.86%     | 0.143  | -3.89%  | -7.08%   |
| ^TYX       | bonds       | +6.90%      | 35.27%     | 0.196  | -2.94%  | -4.88%   |

> **Interpretazione VaR/CVaR**: VaR 95% = -5.18% per BTC-USD significa che nel 5% peggiore delle giornate la perdita supera il 5.18%. CVaR = -8.20% è la perdita media in quelle giornate.

---

## Glossario

| Termine              | Formula / Definizione                                                                                         |
|----------------------|---------------------------------------------------------------------------------------------------------------|
| Rendimento logaritmico | $r_t = \ln(P_t / P_{t-1})$ — additivo nel tempo, simmetrico, approssima il rendimento semplice per valori piccoli |
| Volatilità storica   | $\sigma = \text{std}(r_t)$ — annualizzata moltiplicando per $\sqrt{252}$                                     |
| VaR (Value at Risk)  | Perdita massima non superata con un dato livello di confidenza in un dato orizzonte temporale                 |
| CVaR / Expected Shortfall | Media delle perdite che superano il VaR — misura più conservativa del rischio di coda                 |
| Sharpe Ratio         | $S = \bar{r}_{annual} / \sigma_{annual}$ — rendimento aggiustato per il rischio (qui con risk-free = 0)      |
| Adjusted Close       | Prezzo di chiusura corretto per dividendi e split azionari (fornito da Yahoo Finance con `auto_adjust=True`)  |
| Lag feature          | Valore di una variabile al tempo $t-k$ — usato per catturare la dipendenza seriale nei modelli predittivi    |
| Walk-forward         | Tecnica di validazione out-of-sample in cui la finestra di training scorre nel tempo                          |

---

## Dati on-chain Coin Metrics

`raw_finance.onchain_metrics` contiene osservazioni giornaliere in formato
long con chiave `provider, asset, metric, frequency, observation_time`.
`available_time` è separato da `observation_time` e impedisce l'uso della
misura prima della chiusura del periodo.

Metriche Community integrate: `AdrActCnt`, `TxCnt`, `HashRate`,
`CapMrktCurUSD` e `SplyCur`. Il mart `analytics.fct_model_dataset`
espone rispettivamente `onchain_active_addresses`,
`onchain_transaction_count`, `onchain_hash_rate`,
`onchain_market_cap_usd` e `onchain_current_supply`. Una metrica non
applicabile a una rete, come l'hash rate recente di Ethereum proof-of-stake,
rimane nulla senza interrompere la pipeline.
