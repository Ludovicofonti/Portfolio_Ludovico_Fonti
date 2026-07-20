select
    chart_date,
    country,
    count(*) as chart_rows,
    count(spotify_track_id) as matched_tracks,
    cast(count(spotify_track_id) as numeric) / nullif(count(*), 0) as match_rate,
    count(*) - count(distinct chart_track_id) as duplicate_tracks,
    sum(case when streams is null then 1 else 0 end) as missing_streams,
    cast(0 as integer) as spotify_requests,
    cast(0 as integer) as spotify_retries,
    cast(0 as integer) as spotify_429_responses,
    case
        when count(*) < 190 then 'degraded'
        when cast(count(spotify_track_id) as numeric) / nullif(count(*), 0) < 0.95
            then 'degraded'
        else 'fresh'
    end as pipeline_status
from {{ ref('fct_track_chart_daily') }}
where {{ raw_partition_filter('chart_date') }}
group by 1, 2
