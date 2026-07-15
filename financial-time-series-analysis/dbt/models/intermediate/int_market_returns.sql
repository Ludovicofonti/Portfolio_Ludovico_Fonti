{{ config(materialized='table', enabled=var('enable_crypto_models', false)) }}
select *, ln(close / lag(close) over (partition by exchange, symbol, interval order by open_time)) as return_1,
       (high - low) / nullif(close, 0) as high_low_range,
       close / nullif(open, 0) - 1 as close_open_return,
       taker_buy_quote_volume / nullif(quote_volume, 0) as taker_buy_ratio
from {{ ref('stg_exchange_ohlcv') }}
