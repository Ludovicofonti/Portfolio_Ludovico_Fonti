select
    chart_date,
    country,
    spotify_artist_id,
    artist_name,
    track_count,
    streams,
    cast(streams as numeric)
        / nullif(sum(streams) over (partition by chart_date, country), 0) as market_share,
    artist_stream_rank
from {{ ref('mart_top_artists_italy') }}
where {{ raw_partition_filter('chart_date') }}
