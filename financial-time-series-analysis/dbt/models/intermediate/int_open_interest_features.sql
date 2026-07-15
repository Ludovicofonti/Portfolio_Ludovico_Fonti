{{ config(materialized='table', enabled=var('enable_crypto_models', false)) }}
select *, open_interest / nullif(lag(open_interest) over w, 0) - 1 as open_interest_change,
       ln(open_interest / nullif(lag(open_interest) over w, 0)) as open_interest_log_change,
       (open_interest - avg(open_interest) over w21) / nullif(stddev_samp(open_interest) over w21, 0) as open_interest_zscore
from {{ ref('stg_open_interest') }}
window w as (partition by exchange, symbol order by timestamp),
       w21 as (partition by exchange, symbol order by timestamp rows between 21 preceding and 1 preceding)
