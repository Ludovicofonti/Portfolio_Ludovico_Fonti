with source as (
    select * from {{ source('spotify_raw', 'italy_daily_track_details__artists') }}
),

renamed as (
    select
        _dlt_id,
        _dlt_parent_id as track_details_dlt_id,
        cast(_dlt_list_idx as integer) as artist_order,
        id as spotify_artist_id,
        name as artist_name,
        uri as spotify_artist_uri,
        href as spotify_artist_api_url,
        external_urls__spotify as spotify_artist_url
    from source
    where {{ raw_partition_filter('chart_date') }}
)

select * from renamed
