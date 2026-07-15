{{ config(materialized='table', enabled=var('enable_crypto_models', false)) }}
select * from {{ ref('int_future_targets') }} where interval = '1d'
