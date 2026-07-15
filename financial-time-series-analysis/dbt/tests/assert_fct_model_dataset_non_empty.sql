{{ config(enabled=var('enable_crypto_models', false)) }}

-- Un dataset vuoto è un fallimento operativo anche se tutti gli schemi sono validi.
select 1 as failure
where (select count(*) from {{ ref('fct_model_dataset') }}) = 0
