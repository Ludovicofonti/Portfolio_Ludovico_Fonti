with source as (
    select * from {{ source('spotify_raw', 'italy_daily_track_details') }}
),

renamed as (
    select
        _dlt_id,
        id as spotify_track_id,
        name as spotify_track_name,
        uri as spotify_track_uri,
        href as spotify_track_api_url,
        external_urls__spotify as spotify_track_url,
        external_ids__isrc as isrc,
        cast(duration_ms as integer) as duration_ms,
        cast(duration_ms as numeric) / 60000.0 as duration_minutes,
        cast(explicit as boolean) as is_explicit,
        cast(disc_number as integer) as disc_number,
        cast(track_number as integer) as track_number,
        cast(is_local as boolean) as is_local,
        cast(is_playable as boolean) as is_playable,
        album__id as spotify_album_id,
        album__name as album_name,
        album__album_type as album_type,
        album__release_date as album_release_date_text,
        case
            when album__release_date is null then null
            when length(album__release_date) = 4 then to_date(album__release_date || '-01-01', 'YYYY-MM-DD')
            when length(album__release_date) = 7 then to_date(album__release_date || '-01', 'YYYY-MM-DD')
            else cast(album__release_date as date)
        end as album_release_date,
        album__release_date_precision as album_release_date_precision,
        cast(album__total_tracks as integer) as album_total_tracks,
        album__external_urls__spotify as spotify_album_url,
        chart_track_id,
        cast(chart_date as date) as chart_date,
        chart_country,
        cast(chart_rank as integer) as chart_rank,
        chart_track_name,
        chart_artist_names_text,
        cast(chart_streams as bigint) as chart_streams,
        cast(chart_streams_total as bigint) as chart_streams_total
    from source
)

select * from renamed
