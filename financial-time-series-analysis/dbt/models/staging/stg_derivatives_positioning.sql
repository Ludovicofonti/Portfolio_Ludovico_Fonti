{{ config(materialized='view', enabled=var('enable_crypto_models', false)) }}
select coalesce(ls.exchange, tv.exchange) as exchange,
       coalesce(ls.symbol, tv.symbol) as symbol,
       coalesce(ls.period, tv.period) as period,
       coalesce(ls.timestamp, tv.timestamp) as timestamp,
       cast(ls.long_short_ratio as double) as long_short_ratio,
       cast(ls.long_account_share as double) as long_account_share,
       cast(ls.short_account_share as double) as short_account_share,
       cast(tv.buy_sell_ratio as double) as buy_sell_ratio,
       cast(tv.buy_volume as double) as buy_volume,
       cast(tv.sell_volume as double) as sell_volume,
       greatest(
         cast(ls.available_time as timestamptz),
         cast(tv.available_time as timestamptz)
       ) as available_time,
       greatest(
         cast(ls.ingested_at as timestamptz),
         cast(tv.ingested_at as timestamptz)
       ) as ingested_at
from raw_finance.long_short_ratios ls
full outer join raw_finance.taker_volume_ratios tv
  on ls.exchange = tv.exchange and ls.symbol = tv.symbol
 and ls.period = tv.period and ls.timestamp = tv.timestamp
