{{ config(materialized='table', enabled=var('enable_crypto_models', false)) }}
-- Il forecast origin coincide con la chiusura della candela: solo allora OHLCV
-- e feature derivate dalla candela corrente sono realmente disponibili.
with returns as (
  select *,
         ln(close / nullif(lag(close) over (
           partition by exchange, symbol, interval order by open_time
         ), 0)) as log_return_1
  from {{ ref('stg_exchange_ohlcv') }}
)
select exchange, symbol, interval, close_time as timestamp,
       lead(close, 1) over w / close - 1 as target_return_1,
       lead(close, 4) over w / close - 1 as target_return_4,
       lead(close, 24) over w / close - 1 as target_return_24,
       case when lead(close, 1) over w / close - 1 > 0 then 1 else 0 end as target_direction_1,
       case when lead(close, 4) over w / close - 1 > 0 then 1 else 0 end as target_direction_4,
       case when lead(close, 24) over w / close - 1 > 0 then 1 else 0 end as target_direction_24,
       case
         when lead(close, 1) over w / close - 1 > {{ var('direction_threshold', 0.001) }} then 1
         when lead(close, 1) over w / close - 1 < -{{ var('direction_threshold', 0.001) }} then -1
         else 0
       end as target_direction_neutral_1,
       stddev_samp(log_return_1) over (
         partition by exchange, symbol, interval order by open_time
         rows between 1 following and 24 following
       ) as target_volatility_24,
       min(log_return_1) over (
         partition by exchange, symbol, interval order by open_time
         rows between 1 following and 24 following
       ) as target_tail_return_24
from returns
window w as (partition by exchange, symbol, interval order by open_time)
