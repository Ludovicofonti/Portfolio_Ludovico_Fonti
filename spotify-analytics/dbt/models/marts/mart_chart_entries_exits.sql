with chart as (
    select *
    from {{ ref('fct_track_chart_daily') }}
    where {{ raw_partition_filter('chart_date') }}
),

dated as (
    select
        *,
        dense_rank() over (partition by country order by chart_date) as chart_day_number
    from chart
),

entries as (
    select
        current_row.chart_date,
        current_row.country,
        current_row.chart_track_id,
        current_row.track_name,
        current_row.artist_names_text,
        'entry' as chart_event,
        current_row.chart_rank,
        current_row.streams
    from dated as current_row
    left join dated as previous
        on current_row.country = previous.country
        and current_row.chart_track_id = previous.chart_track_id
        and current_row.chart_day_number = previous.chart_day_number + 1
    where current_row.chart_day_number > 1
      and previous.chart_track_id is null
),

exits as (
    select
        next_day.chart_date,
        previous.country,
        previous.chart_track_id,
        previous.track_name,
        previous.artist_names_text,
        'exit' as chart_event,
        previous.chart_rank,
        previous.streams
    from dated as previous
    inner join (
        select distinct country, chart_date, chart_day_number
        from dated
    ) as next_day
        on previous.country = next_day.country
        and previous.chart_day_number + 1 = next_day.chart_day_number
    left join dated as current_row
        on current_row.country = previous.country
        and current_row.chart_track_id = previous.chart_track_id
        and current_row.chart_day_number = next_day.chart_day_number
    where current_row.chart_track_id is null
)

select * from entries
union all
select * from exits
