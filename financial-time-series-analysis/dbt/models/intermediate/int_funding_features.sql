{{ config(materialized='table', enabled=var('enable_crypto_models', false)) }}
select *, avg(funding_rate) over w as funding_mean,
       (funding_rate - avg(funding_rate) over w) / nullif(stddev_samp(funding_rate) over w, 0) as funding_zscore,
       sum(funding_rate) over (partition by exchange, symbol order by funding_time rows unbounded preceding) as cumulative_funding
from {{ ref('stg_funding_rates') }}
window w as (partition by exchange, symbol order by funding_time rows between 21 preceding and 1 preceding)
