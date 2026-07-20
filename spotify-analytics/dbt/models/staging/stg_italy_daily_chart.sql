with source as (
    select * from {{ source('spotify_raw', 'italy_daily_chart') }}
),

renamed as (
    select
        _dlt_id,
        cast(chart_date as date) as chart_date,
        country,
        country_name,
        chart_source,
        cast(rank as integer) as chart_rank,
        rank_change as rank_change_text,
        case
            when rank_change in ('=', '-', 'NEW', 'RE') then 0
            when rank_change is null or trim(rank_change) = '' then null
            when {{ is_integer("replace(rank_change, '+', '')") }}
                then cast(replace(rank_change, '+', '') as integer)
            else null
        end as rank_change,
        track_id as chart_track_id,
        track_name,
        artist_names_text,
        cast(nullif(days_on_chart, '') as integer) as days_on_chart,
        cast(nullif(peak_rank, '') as integer) as peak_rank,
        peak_count_text,
        cast(streams as bigint) as streams,
        cast(nullif(streams_change, '') as bigint) as streams_change,
        cast(nullif(streams_7day, '') as bigint) as streams_7day,
        cast(nullif(streams_7day_change, '') as bigint) as streams_7day_change,
        cast(nullif(streams_total, '') as bigint) as streams_total,
        kworb_track_url
    from source
    where {{ raw_partition_filter('chart_date') }}
)

select * from renamed
