select
    chart_date,
    country,
    chart_track_id,
    track_name,
    artist_names_text,
    album_name,
    album_type,
    album_release_date,
    {{ month_start('album_release_date') }} as release_cohort_month,
    days_since_release,
    release_stage,
    collaboration_type,
    is_explicit,
    chart_rank,
    streams,
    streams_change,
    days_on_chart,
    peak_rank
from {{ ref('rpt_track_opportunities_daily') }}
where album_release_date is not null
