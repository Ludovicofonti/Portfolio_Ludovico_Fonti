{{
    config(
        materialized='incremental',
        unique_key=['chart_date', 'country', 'chart_track_id'],
        incremental_strategy='merge',
        incremental_predicates=[
            "DBT_INTERNAL_DEST.chart_date >= date_sub(current_date(), interval 365 day)"
        ]
    )
}}

select *
from {{ ref('int_italy_chart_enriched') }}
{% if is_incremental() %}
where chart_date >= (
    select coalesce(max(chart_date), cast('1900-01-01' as date))
    from {{ this }}
    where {{ raw_partition_filter('chart_date') }}
)
{% endif %}
