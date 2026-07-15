{{ config(materialized='table', enabled=var('enable_crypto_models', false)) }}
select provider,
       case lower(asset)
         when 'btc' then 'BTCUSDT'
         when 'eth' then 'ETHUSDT'
         else upper(asset)
       end as symbol,
       frequency,
       available_time,
       max(value) filter (where metric = 'AdrActCnt') as onchain_active_addresses,
       max(value) filter (where metric = 'TxCnt') as onchain_transaction_count,
       max(value) filter (where metric = 'HashRate') as onchain_hash_rate,
       max(value) filter (where metric = 'CapMrktCurUSD') as onchain_market_cap_usd,
       max(value) filter (where metric = 'SplyCur') as onchain_current_supply
from {{ ref('stg_onchain_metrics') }}
group by provider, asset, frequency, available_time
