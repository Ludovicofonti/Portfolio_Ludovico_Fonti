{{ config(materialized='table', enabled=var('enable_crypto_models', false)) }}
select *,
       (basis_rate - avg(basis_rate) over w)
         / nullif(stddev_samp(basis_rate) over w, 0) as basis_zscore,
       basis_rate - lag(basis_rate) over (
         partition by exchange, symbol, period order by timestamp
       ) as basis_change
from {{ ref('stg_basis_metrics') }}
window w as (
  partition by exchange, symbol, period order by timestamp
  rows between 21 preceding and 1 preceding
)
