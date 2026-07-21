with songs as (
    select *
    from {{ ref('mart_top_songs_italy') }}
    where {{ raw_partition_filter('chart_date') }}
),

classified as (
    select
        *,
        case
            when chart_rank <= 10 then 'Top 10'
            when chart_rank <= 50 then '11-50'
            when chart_rank <= 100 then '51-100'
            else '101-200'
        end as rank_segment,
        case
            when days_since_release is null then 'Unknown'
            when days_since_release <= 60 then 'Fresh'
            when days_since_release <= 180 then 'Developing'
            else 'Catalog'
        end as release_stage,
        case when is_collaboration then 'Collaboration' else 'Solo artist' end
            as collaboration_type,
        case
            when rank_change > 0 then 'Rank up'
            when rank_change < 0 then 'Rank down'
            else 'Rank stable'
        end as rank_momentum,
        case
            when streams_change > 0 then 'Streams up'
            when streams_change < 0 then 'Streams down'
            else 'Streams stable'
        end as streams_momentum,
        case
            when rank_change > 0 and streams_change > 0 and chart_rank <= 50 then 'Accelerate'
            when chart_rank <= 20 and (streams_change < 0 or rank_change < 0) then 'Defend'
            when days_on_chart >= 30 and streams_change > 0 then 'Extend'
            when streams_change < 0 and rank_change < 0 then 'Reduce risk'
            else 'Monitor'
        end as action_label,
        case
            when rank_change > 0 and streams_change > 0 and chart_rank <= 50
                then 'Increase paid, social and playlist support'
            when chart_rank <= 20 and (streams_change < 0 or rank_change < 0)
                then 'Defend playlists and content frequency'
            when days_on_chart >= 30 and streams_change > 0
                then 'Extend radio, editorial and evergreen content'
            when streams_change < 0 and rank_change < 0
                then 'Review churn, competition and creative fatigue'
            else 'Monitor before reallocating budget'
        end as recommended_action,
        case
            when rank_change > 0 and streams_change > 0 and chart_rank <= 50 then 1
            when chart_rank <= 20 and (streams_change < 0 or rank_change < 0) then 2
            when days_on_chart >= 30 and streams_change > 0 then 3
            when streams_change < 0 and rank_change < 0 then 4
            else 5
        end as action_priority,
        abs(coalesce(streams_change, 0)) + 1 as movement_size
    from songs
)

select * from classified
