{{ config(materialized='view', enabled=var('enable_crypto_models', false)) }}
select exchange, symbol, cast(funding_time as timestamptz) as funding_time,
       cast(funding_rate as double) as funding_rate, cast(mark_price as double) as mark_price,
       cast(available_time as timestamptz) as available_time, cast(ingested_at as timestamptz) as ingested_at
from raw_finance.funding_rates
