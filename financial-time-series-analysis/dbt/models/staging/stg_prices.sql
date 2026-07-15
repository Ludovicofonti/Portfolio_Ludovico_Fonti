{{
  config(
    materialized='view',
    tags=['staging', 'prices']
  )
}}

-- Unione di tutte le asset class in un'unica tabella normalizzata
{% set asset_classes = ['stocks', 'crypto', 'forex', 'commodities', 'indices', 'bonds'] %}

{% for cls in asset_classes %}
SELECT
    symbol,
    '{{ cls }}'     AS asset_class,
    date::DATE      AS date,
    open::DOUBLE    AS open,
    high::DOUBLE    AS high,
    low::DOUBLE     AS low,
    close::DOUBLE   AS close,
    volume::DOUBLE  AS volume
FROM {{ source('raw_finance', 'prices_' ~ cls) }}
WHERE close IS NOT NULL
  AND date IS NOT NULL
{% if not loop.last %} UNION ALL {% endif %}
{% endfor %}
