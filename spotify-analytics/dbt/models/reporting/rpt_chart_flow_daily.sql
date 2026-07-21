select
    chart_date,
    country,
    chart_track_id,
    track_name,
    artist_names_text,
    chart_event,
    case when chart_event = 'entry' then 1 else -1 end as event_direction,
    chart_rank,
    streams
from {{ ref('mart_chart_entries_exits') }}
where {{ raw_partition_filter('chart_date') }}
