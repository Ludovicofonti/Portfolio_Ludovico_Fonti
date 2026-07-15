select exchange, symbol, interval, forecast_origin, count(*) as records
from {{ ref('fct_model_dataset') }}
group by 1, 2, 3, 4
having count(*) > 1
