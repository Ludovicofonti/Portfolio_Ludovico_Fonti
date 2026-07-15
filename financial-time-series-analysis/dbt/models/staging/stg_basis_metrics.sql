{{ config(materialized='view', enabled=var('enable_crypto_models', false)) }}
select exchange, symbol, period, cast(timestamp as timestamptz) as timestamp,
       cast(index_price as double) as index_price,
       cast(futures_price as double) as futures_price,
       cast(basis as double) as basis,
       cast(basis_rate as double) as basis_rate,
       cast(available_time as timestamptz) as available_time,
       cast(ingested_at as timestamptz) as ingested_at
from raw_finance.basis_metrics
