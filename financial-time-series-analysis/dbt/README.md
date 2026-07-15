# Modelli dbt

Il progetto dbt trasforma i dati grezzi locali in dataset point-in-time per analisi e valutazione.

## Livelli

- staging: normalizzazione delle fonti;
- intermediate: join temporali e feature intermedie;
- features: mart per feature giornaliere e orarie;
- marts: target, rendimenti, rischio e dataset per i modelli.

## Verifica

    uv run dbt parse --project-dir dbt --profiles-dir dbt --vars "{enable_crypto_models: true}"
    uv run dbt build --project-dir dbt --profiles-dir dbt --vars "{enable_crypto_models: true}"

Il profilo usa un database DuckDB relativo sotto data. Database, log e target dbt sono esclusi dal repository.
