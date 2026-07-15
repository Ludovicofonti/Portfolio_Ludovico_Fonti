{{ config(materialized='table', enabled=var('enable_crypto_models', false)) }}
select *,
       spread / nullif(mid_price, 0) as relative_spread,
       (bid_depth_1pct + ask_depth_1pct) as depth_1pct
from {{ ref('stg_exchange_orderbook') }}
