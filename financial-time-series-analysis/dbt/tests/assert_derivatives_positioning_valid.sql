select *
from {{ ref('stg_derivatives_positioning') }}
where long_short_ratio <= 0
   or long_account_share < 0 or long_account_share > 1
   or short_account_share < 0 or short_account_share > 1
   or buy_sell_ratio <= 0
   or buy_volume < 0 or sell_volume < 0
   or available_time > ingested_at
