with ranked as (
    select
        *,
        row_number() over (
            partition by country, chart_track_id
            order by chart_date desc
        ) as recency_rank
    from {{ ref('fct_track_chart_daily') }}
    where {{ raw_partition_filter('chart_date') }}
)

select
    country,
    chart_track_id,
    max(track_name) as track_name,
    max(artist_names_text) as artist_names_text,
    min(chart_date) as first_chart_date,
    max(chart_date) as latest_chart_date,
    count(*) as chart_days_observed,
    min(chart_rank) as observed_peak_rank,
    sum(streams) as observed_streams,
    max(case when recency_rank = 1 then chart_rank end) as current_rank,
    max(case when recency_rank = 1 then rank_change end) as current_rank_change,
    max(case when recency_rank = 1 then streams_change end) as current_streams_change,
    case
        when max(case when recency_rank = 1 then rank_change end) > 0 then 'rising'
        when max(case when recency_rank = 1 then rank_change end) < 0 then 'declining'
        else 'resilient'
    end as lifecycle_status
from ranked
group by 1, 2
