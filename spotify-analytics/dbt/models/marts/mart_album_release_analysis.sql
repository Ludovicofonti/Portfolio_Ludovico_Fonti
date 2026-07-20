select
    chart_date,
    country,
    spotify_album_id,
    album_name,
    album_type,
    spotify_album_url,
    album_image_url,
    album_release_date,
    release_year,
    album_total_tracks,
    count(*) as chart_track_count,
    sum(streams) as streams,
    min(chart_rank) as best_rank,
    cast(avg(days_since_release) as numeric) as average_days_since_release,
    {{ aggregate_boolean_or('is_explicit') }} as has_explicit_track
from {{ ref('int_italy_chart_enriched') }}
where spotify_album_id is not null
group by 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
