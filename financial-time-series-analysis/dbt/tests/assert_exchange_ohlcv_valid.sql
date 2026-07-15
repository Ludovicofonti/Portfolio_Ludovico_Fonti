select *
from {{ ref('stg_exchange_ohlcv') }}
where open <= 0 or high <= 0 or low <= 0 or close <= 0
   or base_volume < 0 or quote_volume < 0
   or high < greatest(open, close, low)
   or low > least(open, close, high)
   or close_time <= open_time
   or available_time > ingested_at
