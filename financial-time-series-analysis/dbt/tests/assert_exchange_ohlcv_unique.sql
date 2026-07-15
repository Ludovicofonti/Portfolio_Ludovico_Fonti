select exchange, symbol, interval, open_time, count(*) as records
from {{ ref('stg_exchange_ohlcv') }}
group by 1, 2, 3, 4
having count(*) > 1
