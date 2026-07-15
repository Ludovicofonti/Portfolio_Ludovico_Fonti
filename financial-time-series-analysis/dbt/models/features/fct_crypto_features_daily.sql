{{ config(materialized='table', enabled=var('enable_crypto_models', false)) }}
select r.* exclude (available_time),
       r.available_time as market_available_time,
       f.funding_rate, f.funding_zscore, f.available_time as funding_available_time,
       oi.open_interest_change, oi.open_interest_zscore, oi.available_time as open_interest_available_time,
       ob.spread_bps, ob.order_book_imbalance, ob.depth_1pct,
       ob.available_time as orderbook_available_time,
       p.long_short_ratio, p.long_short_zscore, p.buy_sell_ratio, p.buy_sell_zscore,
       p.available_time as positioning_available_time,
       b.basis_rate, b.basis_zscore, b.basis_change,
       b.available_time as basis_available_time,
       oc.onchain_active_addresses, oc.onchain_transaction_count,
       oc.onchain_hash_rate, oc.onchain_market_cap_usd,
       oc.onchain_current_supply, oc.available_time as onchain_available_time,
       greatest(
         r.available_time,
         coalesce(f.available_time, r.available_time),
         coalesce(oi.available_time, r.available_time),
         coalesce(ob.available_time, r.available_time),
         coalesce(p.available_time, r.available_time),
         coalesce(b.available_time, r.available_time),
         coalesce(oc.available_time, r.available_time)
       ) as available_time
from {{ ref('int_market_returns') }} r
asof left join {{ ref('int_funding_features') }} f
  on r.symbol = f.symbol and r.close_time >= f.available_time
asof left join {{ ref('int_open_interest_features') }} oi
  on r.symbol = oi.symbol and r.close_time >= oi.available_time
asof left join {{ ref('int_market_microstructure') }} ob
  on r.symbol = ob.symbol and r.close_time >= ob.available_time
asof left join {{ ref('int_positioning_features') }} p
  on r.symbol = p.symbol and r.close_time >= p.available_time
asof left join {{ ref('int_basis_features') }} b
  on r.symbol = b.symbol and r.close_time >= b.available_time
asof left join {{ ref('int_onchain_features') }} oc
  on r.symbol = oc.symbol and r.close_time >= oc.available_time
where r.interval = '1d'
