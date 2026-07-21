select
    chart_date,
    country,
    spotify_artist_id,
    artist_name,
    track_count,
    streams,
    market_share,
    artist_stream_rank,
    case
        when artist_stream_rank <= 5 then 'Top 5'
        when artist_stream_rank <= 15 then 'Top 15'
        else 'Long tail'
    end as artist_segment
from {{ ref('mart_artist_market_share') }}
where {{ raw_partition_filter('chart_date') }}
