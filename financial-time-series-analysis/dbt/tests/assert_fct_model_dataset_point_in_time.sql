{{ config(enabled=var('enable_crypto_models', false)) }}

-- Nessuna feature può essere pubblicata dopo il forecast origin.
select *
from {{ ref('fct_model_dataset') }}
where available_time > forecast_origin
