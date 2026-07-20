select chart_date, country, chart_track_id, count(*) as row_count
from {{ ref('fct_track_chart_daily') }}
where {{ raw_partition_filter('chart_date') }}
group by 1, 2, 3
having count(*) > 1
