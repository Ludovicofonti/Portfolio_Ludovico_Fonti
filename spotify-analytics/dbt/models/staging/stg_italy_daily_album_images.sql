with source as (
    select * from {{ source('spotify_raw', 'italy_daily_track_details__album__images') }}
),

ranked as (
    select
        _dlt_parent_id as track_details_dlt_id,
        url as album_image_url,
        cast(height as integer) as image_height,
        cast(width as integer) as image_width,
        row_number() over (
            partition by _dlt_parent_id
            order by cast(width as integer) desc nulls last
        ) as image_rank
    from source
    where {{ raw_partition_filter('chart_date') }}
)

select * from ranked
