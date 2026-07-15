{{ config(materialized='table', enabled=var('enable_crypto_models', false)) }}
select *,
       (long_short_ratio - avg(long_short_ratio) over w)
         / nullif(stddev_samp(long_short_ratio) over w, 0) as long_short_zscore,
       (buy_sell_ratio - avg(buy_sell_ratio) over w)
         / nullif(stddev_samp(buy_sell_ratio) over w, 0) as buy_sell_zscore
from {{ ref('stg_derivatives_positioning') }}
window w as (
  partition by exchange, symbol, period order by timestamp
  rows between 21 preceding and 1 preceding
)
