with songs as (
    select *
    from {{ ref('mart_top_songs_italy') }}
    where {{ raw_partition_filter('chart_date') }}
)

select
    chart_date,
    country,
    count(distinct chart_track_id) as track_count,
    sum(streams) as streams,
    sum(streams_change) as streams_change,
    sum(case when chart_rank <= 10 then streams else 0 end) as top_10_streams,
    sum(case when chart_rank <= 50 then streams else 0 end) as top_50_streams,
    cast(sum(case when chart_rank <= 10 then streams else 0 end) as numeric)
        / nullif(sum(streams), 0) as top_10_stream_share,
    cast(sum(case when chart_rank <= 50 then streams else 0 end) as numeric)
        / nullif(sum(streams), 0) as top_50_stream_share,
    avg(case when is_collaboration then 1.0 else 0.0 end) as collaboration_share,
    avg(case when is_explicit then 1.0 else 0.0 end) as explicit_share,
    avg(days_on_chart) as avg_days_on_chart,
    sum(case when days_since_release <= 60 then streams else 0 end) as fresh_streams,
    sum(case when days_since_release between 61 and 180 then streams else 0 end)
        as developing_streams,
    sum(case when days_since_release > 180 then streams else 0 end) as catalog_streams
from songs
group by 1, 2
