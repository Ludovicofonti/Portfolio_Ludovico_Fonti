with chart as (
    select * from {{ ref('stg_italy_daily_chart') }}
),

track_details as (
    select * from {{ ref('stg_italy_daily_track_details') }}
),

artist_counts as (
    select
        track_details_dlt_id,
        count(*) as artist_count
    from {{ ref('stg_italy_daily_track_artists') }}
    group by 1
),

album_images as (
    select
        track_details_dlt_id,
        album_image_url
    from {{ ref('stg_italy_daily_album_images') }}
    where image_rank = 1
),

top_200_totals as (
    select
        chart_date,
        country,
        sum(streams) as top_200_streams
    from chart
    group by 1, 2
)

select
    chart.chart_date,
    chart.country,
    chart.country_name,
    chart.chart_source,
    chart.chart_rank,
    chart.rank_change,
    chart.rank_change_text,
    chart.chart_track_id,
    chart.track_name,
    chart.artist_names_text,
    chart.days_on_chart,
    chart.peak_rank,
    chart.peak_count_text,
    chart.streams,
    chart.streams_change,
    chart.streams_7day,
    chart.streams_7day_change,
    chart.streams_total,
    chart.kworb_track_url,
    track_details.spotify_track_id,
    track_details.spotify_track_name,
    track_details.spotify_track_url,
    track_details.spotify_album_id,
    track_details.album_name,
    track_details.album_type,
    track_details.album_release_date,
    track_details.album_release_date_precision,
    track_details.album_total_tracks,
    track_details.spotify_album_url,
    track_details.duration_ms,
    track_details.duration_minutes,
    track_details.is_explicit,
    track_details.is_playable,
    track_details.isrc,
    coalesce(artist_counts.artist_count, 0) as artist_count,
    coalesce(artist_counts.artist_count, 0) > 1 as is_collaboration,
    album_images.album_image_url,
    top_200_totals.top_200_streams,
    cast(chart.streams as numeric) / nullif(top_200_totals.top_200_streams, 0) as streams_share,
    case
        when chart.chart_rank <= 10 then 'Top 10'
        when chart.chart_rank <= 50 then 'Top 50'
        when chart.chart_rank <= 100 then 'Top 100'
        else 'Top 200'
    end as rank_bucket,
    cast(extract(year from track_details.album_release_date) as integer) as release_year,
    {{ date_diff_days('chart.chart_date', 'track_details.album_release_date') }}
        as days_since_release
from chart
left join track_details
    on chart.chart_track_id = track_details.chart_track_id
    and chart.chart_date = track_details.chart_date
left join artist_counts
    on track_details._dlt_id = artist_counts.track_details_dlt_id
left join album_images
    on track_details._dlt_id = album_images.track_details_dlt_id
left join top_200_totals
    on chart.chart_date = top_200_totals.chart_date
    and chart.country = top_200_totals.country
