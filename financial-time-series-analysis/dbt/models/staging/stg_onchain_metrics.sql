{{ config(materialized='view', enabled=var('enable_crypto_models', false)) }}
{% set relation = adapter.get_relation(
    database=target.database, schema='raw_finance', identifier='onchain_metrics'
) %}
{% if relation %}
select provider, lower(asset) as asset, metric, frequency,
       cast(observation_time as timestamptz) as observation_time,
       cast(value as double) as value,
       cast(available_time as timestamptz) as available_time,
       cast(ingested_at as timestamptz) as ingested_at,
       coalesce(quality_flag, 'valid') as quality_flag
from {{ source('raw_finance', 'onchain_metrics') }}
where cast(available_time as timestamptz) <= cast(ingested_at as timestamptz)
  and coalesce(quality_flag, 'valid') = 'valid'
{% else %}
select cast(null as varchar) as provider, cast(null as varchar) as asset,
       cast(null as varchar) as metric, cast(null as varchar) as frequency,
       cast(null as timestamptz) as observation_time, cast(null as double) as value,
       cast(null as timestamptz) as available_time,
       cast(null as timestamptz) as ingested_at,
       cast(null as varchar) as quality_flag
where false
{% endif %}
