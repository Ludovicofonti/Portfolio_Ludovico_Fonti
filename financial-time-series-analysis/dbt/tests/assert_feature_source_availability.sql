select *
from {{ ref('fct_model_dataset') }}
where available_time > forecast_origin
   or market_available_time > forecast_origin
   or funding_available_time > forecast_origin
   or open_interest_available_time > forecast_origin
   or orderbook_available_time > forecast_origin
   or positioning_available_time > forecast_origin
   or basis_available_time > forecast_origin
