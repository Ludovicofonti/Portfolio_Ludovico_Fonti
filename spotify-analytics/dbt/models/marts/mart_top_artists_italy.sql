with artists as (
    select
        details.chart_date,
        details.chart_country as country,
        artist.spotify_artist_id,
        artist.artist_name,
        artist.spotify_artist_url,
        details.chart_rank,
        details.chart_streams,
        details.spotify_track_id,
        details.chart_track_id
    from {{ ref('stg_italy_daily_track_details') }} as details
    inner join {{ ref('stg_italy_daily_track_artists') }} as artist
        on details._dlt_id = artist.track_details_dlt_id
),

aggregated as (
    select
        chart_date,
        country,
        spotify_artist_id,
        artist_name,
        spotify_artist_url,
        count(distinct spotify_track_id) as track_count,
        sum(chart_streams) as streams,
        min(chart_rank) as best_rank,
        avg(chart_rank)::numeric(10, 2) as average_rank
    from artists
    group by 1, 2, 3, 4, 5
)

select
    *,
    dense_rank() over (
        partition by chart_date, country
        order by streams desc
    ) as artist_stream_rank
from aggregated
