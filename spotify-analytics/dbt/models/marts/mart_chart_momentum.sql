select
    chart_date,
    chart_rank,
    track_name,
    artist_names_text,
    album_name,
    streams,
    streams_change,
    rank_change,
    days_on_chart,
    peak_rank,
    case
        when rank_change > 0 then 'Rising'
        when rank_change < 0 then 'Falling'
        else 'Stable'
    end as rank_momentum,
    case
        when streams_change > 0 then 'Streams up'
        when streams_change < 0 then 'Streams down'
        else 'Streams stable'
    end as streams_momentum,
    album_image_url,
    spotify_track_url
from {{ ref('int_italy_chart_enriched') }}
