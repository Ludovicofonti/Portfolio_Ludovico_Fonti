{{ config(materialized='table', enabled=var('enable_crypto_models', false)) }}
with features as (
  select * from {{ ref('fct_crypto_features_hourly') }}
  union all by name
  select * from {{ ref('fct_crypto_features_daily') }}
),
targets as (
  select * from {{ ref('fct_crypto_targets_hourly') }}
  union all by name
  select * from {{ ref('fct_crypto_targets_daily') }}
)
select f.*, t.timestamp as forecast_origin,
       t.target_return_1, t.target_return_4, t.target_return_24,
       t.target_direction_1, t.target_direction_4, t.target_direction_24,
       t.target_direction_neutral_1, t.target_volatility_24, t.target_tail_return_24
from features f
join targets t
  on f.exchange=t.exchange and f.symbol=t.symbol and f.interval=t.interval and f.close_time=t.timestamp
where f.available_time <= t.timestamp
  and t.target_return_1 is not null
