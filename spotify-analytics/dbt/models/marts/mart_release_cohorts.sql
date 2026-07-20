select
    chart_date,
    country,
    {{ month_start('album_release_date') }} as release_cohort_month,
    count(distinct chart_track_id) as chart_tracks,
    sum(streams) as streams,
    avg(chart_rank) as average_rank,
    avg(days_since_release) as average_days_since_release
from {{ ref('fct_track_chart_daily') }}
where {{ raw_partition_filter('chart_date') }}
  and album_release_date is not null
group by 1, 2, 3
