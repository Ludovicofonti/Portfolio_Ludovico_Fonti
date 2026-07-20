select chart_date, country
from {{ ref('fct_track_chart_daily') }}
where {{ raw_partition_filter('chart_date') }}
group by 1, 2
having cast(count(spotify_track_id) as numeric) / nullif(count(*), 0) < 0.95
