select
    chart_date,
    country,
    sum(streams) as top_200_streams,
    sum(case when chart_rank <= 10 then streams else 0 end) as top_10_streams,
    sum(case when chart_rank <= 50 then streams else 0 end) as top_50_streams,
    cast(sum(case when chart_rank <= 10 then streams else 0 end) as numeric)
        / nullif(sum(streams), 0) as top_10_stream_share,
    cast(sum(case when chart_rank <= 50 then streams else 0 end) as numeric)
        / nullif(sum(streams), 0) as top_50_stream_share
from {{ ref('fct_track_chart_daily') }}
where {{ raw_partition_filter('chart_date') }}
group by 1, 2
