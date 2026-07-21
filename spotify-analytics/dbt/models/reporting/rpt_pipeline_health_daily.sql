with health as (
    select *
    from {{ ref('mart_data_quality_daily') }}
    where {{ raw_partition_filter('chart_date') }}
)

select
    chart_date,
    country,
    chart_rows,
    matched_tracks,
    match_rate,
    duplicate_tracks,
    missing_streams,
    spotify_requests,
    spotify_retries,
    spotify_429_responses,
    pipeline_status,
    min(chart_date) over (partition by country) as history_start,
    max(chart_date) over (partition by country) as latest_chart_date,
    count(*) over (partition by country) as history_days,
    sum(chart_rows) over (partition by country) as observations
from health
