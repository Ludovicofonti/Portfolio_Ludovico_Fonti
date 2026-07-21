select
    country,
    chart_track_id,
    track_name,
    artist_names_text,
    first_chart_date,
    latest_chart_date,
    chart_days_observed,
    observed_peak_rank,
    observed_streams,
    current_rank,
    current_rank_change,
    current_streams_change,
    lifecycle_status,
    case lifecycle_status
        when 'rising' then 1
        when 'resilient' then 2
        else 3
    end as lifecycle_sort_order
from {{ ref('mart_track_lifecycle') }}
