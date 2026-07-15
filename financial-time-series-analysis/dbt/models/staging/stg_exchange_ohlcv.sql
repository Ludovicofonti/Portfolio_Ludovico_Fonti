{{ config(materialized='view', enabled=var('enable_crypto_models', false)) }}
select exchange, symbol, interval, cast(open_time as timestamptz) as open_time,
       cast(close_time as timestamptz) as close_time, cast(open as double) as open,
       cast(high as double) as high, cast(low as double) as low, cast(close as double) as close,
       cast(base_volume as double) as base_volume, cast(quote_volume as double) as quote_volume,
       cast(number_of_trades as bigint) as number_of_trades,
       cast(taker_buy_base_volume as double) as taker_buy_base_volume,
       cast(taker_buy_quote_volume as double) as taker_buy_quote_volume,
       cast(available_time as timestamptz) as available_time, cast(ingested_at as timestamptz) as ingested_at,
       coalesce(quality_flag, 'valid') as quality_flag
from raw_finance.exchange_ohlcv
where cast(close_time as timestamptz) <= cast(ingested_at as timestamptz)
