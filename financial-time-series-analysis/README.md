# Financial Time Series Research Platform

Piattaforma personale e didattica per costruire pipeline riproducibili di ricerca quantitativa su serie temporali finanziarie. Il progetto integra acquisizione dati, trasformazioni point-in-time, feature engineering, valutazione walk-forward, controllo del rischio e reportistica.

Il repository contiene codice, configurazioni di esempio e report dimostrativi sintetici. Non contiene credenziali, database locali, output di esecuzioni reali o dati proprietari.

> Le analisi hanno finalità esclusivamente didattiche e non costituiscono consulenza finanziaria, sollecitazione all'investimento o promessa di performance.

## Cosa dimostra

- Data engineering incrementale con dlt e DuckDB.
- Modellazione SQL e controlli di qualità con dbt.
- Feature engineering temporale, di mercato, derivati, macro e on-chain.
- Forecast di rendimento, direzione, volatilità e rischio di coda.
- Baseline obbligatorie e validazione walk-forward senza leakage.
- Simulazione di costi di transazione e metriche di portafoglio.
- Backtesting di VaR, Expected Shortfall ed eventi estremi.
- Registry locale degli esperimenti e report tecnici/business.

## Architettura

    Fonti pubbliche / API
            |
            v
    dlt ingestion incrementale
            |
            v
    DuckDB raw -> dbt staging/intermediate/marts
            |
            v
    Feature e target point-in-time
            |
            v
    Baseline + modelli + walk-forward
            |
            v
    Costi, rischio, gate decisionali e report

La descrizione completa dei componenti è in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Le tabelle e i campi principali sono documentati in [DATA_DICTIONARY.md](DATA_DICTIONARY.md).

## Casi d'uso

1. Confrontare un modello di previsione dei rendimenti con baseline semplici.
2. Valutare segnali direzionali al netto dei costi di transazione.
3. Stimare volatilità condizionale e rischio di coda.
4. Analizzare stabilità delle performance tra regimi di mercato.
5. Costruire dataset point-in-time per ricerca quantitativa riproducibile.

Dettagli, input e output attesi sono descritti in [docs/USE_CASES.md](docs/USE_CASES.md).

## Quick start

Requisiti:

- Python 3.11 o successivo.
- uv.
- Accesso di rete alle fonti pubbliche abilitate.

Installazione:

    uv sync --locked --extra dev

Verifica della CLI:

    uv run financial-ts --help
    uv run financial-ts status

Esecuzione end-to-end di esempio:

    uv run financial-ts run --symbol BTCUSDT --interval 1h --task return --horizon 1

Valutazione su mart già disponibili:

    uv run financial-ts evaluate --symbol BTCUSDT --interval 1h --task volatility --horizon 24

Rigenerazione di un report da una run tracciata:

    uv run financial-ts report --run-id RUN_ID

Gli output vengono creati nelle cartelle data e reports e sono esclusi dal versionamento.

## Configurazione delle credenziali

Copiare [.env.example](.env.example) e impostare le variabili solo nell'ambiente locale o nel secret store della piattaforma di esecuzione.

Esempio PowerShell:

    $env:FRED_API_KEY = "valore-locale"
    $env:COINMETRICS_API_KEY = "valore-locale-opzionale"

Il codice legge le chiavi da variabili d'ambiente. Nessun valore reale deve essere inserito nei file YAML, nei README o nel repository.

## Fonti dati supportate

| Fonte | Ambito | Credenziali |
|---|---|---|
| Binance Spot | OHLCV e microstruttura | Non richieste per gli endpoint pubblici usati |
| Binance Futures | funding, open interest e positioning | Non richieste per gli endpoint pubblici usati |
| Coin Metrics Community | metriche on-chain | Opzionali, via COINMETRICS_API_KEY |
| FRED / ALFRED | serie macroeconomiche e vintage | FRED_API_KEY |
| Yahoo Finance | flusso legacy di acquisizione | Dipende dai termini del provider |

Prima di utilizzare o redistribuire i dati è necessario verificare termini, licenze e limiti della fonte.

## Task quantitativi

| Task | Esempi di modelli | Controlli principali |
|---|---|---|
| Rendimento | ridge, ARIMA, SARIMA | MAE, confronto baseline, Diebold-Mariano |
| Direzione | classificatore lineare | accuracy bilanciata, hit rate, costi |
| Volatilità | GARCH Student-t | stabilità, calibrazione, coverage |
| Rischio di coda | quantile/ridge ed EVT | VaR, Expected Shortfall, test di violazione |

La selezione del modello non dipende soltanto da una metrica predittiva: il gate considera baseline, robustezza temporale, costi e rischio.

## Report dimostrativi

Gli esempi seguenti sono sintetici e servono esclusivamente a mostrare il formato degli output:

- [Report forecast](examples/reports/FORECAST_REPORT.md)
- [Report rischio](examples/reports/RISK_REPORT.md)
- [Report strategia](examples/reports/STRATEGY_REPORT.md)

Nessun valore nei report di esempio deriva da una run reale o rappresenta una performance ottenuta.

## Struttura del repository

    analysis/       analisi statistiche delle serie
    baselines/      benchmark semplici per ogni task
    config/         configurazioni dichiarative versionabili
    dbt/            trasformazioni SQL e test di qualità
    docs/           architettura e casi d'uso
    evaluation/     walk-forward, metriche e risk backtesting
    examples/       report sintetici pubblicabili
    experiments/    metadata e registry delle run
    features/       feature point-in-time e controlli anti-leakage
    legacy/         prototipi storici conservati a riferimento
    models/         modelli previsionali e di rischio
    pipelines/      ingestion e orchestrazione
    reporting/      report tecnici, business e grafici
    strategy/       segnali, costi, sizing e metriche
    tests/          test unitari, temporali e di integrazione

Database, cache, log, report generati e artefatti degli esperimenti non fanno parte del repository.

## Test e qualità

    uv run python -m pytest
    uv run python -m compileall -q .
    uv run dbt parse --project-dir dbt --profiles-dir dbt --vars "{enable_crypto_models: true}"

La CI esegue questi controlli su Python 3.11, 3.12 e 3.13.

## Sicurezza e privacy

Consultare [SECURITY.md](SECURITY.md). In sintesi:

- nessuna credenziale deve essere committata;
- database e report di esecuzione restano locali;
- i dati personali o proprietari non sono ammessi;
- i report pubblici devono usare dati sintetici o fonti redistribuibili.
