{{ config(materialized='view', enabled=var('enable_crypto_models', false)) }}
select exchange, symbol, cast(timestamp as timestamptz) as timestamp,
       cast(open_interest as double) as open_interest, cast(open_interest_value as double) as open_interest_value,
       cast(available_time as timestamptz) as available_time, cast(ingested_at as timestamptz) as ingested_at
from raw_finance.open_interest
