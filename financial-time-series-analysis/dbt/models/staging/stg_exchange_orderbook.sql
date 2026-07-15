{{ config(materialized='view', enabled=var('enable_crypto_models', false)) }}
select exchange, symbol,
       cast(snapshot_time as timestamptz) as snapshot_time,
       cast(best_bid as double) as best_bid,
       cast(best_ask as double) as best_ask,
       cast(mid_price as double) as mid_price,
       cast(spread as double) as spread,
       cast(spread_bps as double) as spread_bps,
       cast(bid_depth_1pct as double) as bid_depth_1pct,
       cast(ask_depth_1pct as double) as ask_depth_1pct,
       cast(order_book_imbalance as double) as order_book_imbalance,
       cast(available_time as timestamptz) as available_time,
       cast(ingested_at as timestamptz) as ingested_at
from raw_finance.exchange_orderbook
