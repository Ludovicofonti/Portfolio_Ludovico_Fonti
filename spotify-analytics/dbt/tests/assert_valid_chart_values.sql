select *
from {{ ref('fct_track_chart_daily') }}
where {{ raw_partition_filter('chart_date') }}
  and (
      chart_rank not between 1 and 200
      or streams < 0
      or chart_date > current_date
      or peak_rank > chart_rank
  )
