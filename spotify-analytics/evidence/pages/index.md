---
title: Spotify Italy Analytics
---

```sql chart_snapshot
with filtered_songs as (
    select *
    from spotify_public.mart_top_songs_italy
    where
        ('${inputs.rank_scope.value}' = 'All' or rank_bucket = '${inputs.rank_scope.value}')
        and streams >= cast('${inputs.min_streams.value}' as integer)
        and (
            '${inputs.collab_scope.value}' = 'All'
            or ('${inputs.collab_scope.value}' = 'Collaborazioni' and is_collaboration)
            or ('${inputs.collab_scope.value}' = 'Solo artist' and not is_collaboration)
        )
        and (
            '${inputs.release_scope.value}' = 'All'
            or ('${inputs.release_scope.value}' = 'Fresh' and days_since_release <= 60)
            or ('${inputs.release_scope.value}' = 'Developing' and days_since_release between 61 and 180)
            or ('${inputs.release_scope.value}' = 'Catalog' and days_since_release > 180)
        )
)
select
    max(chart_date) as chart_date,
    count(*) as tracks,
    sum(streams) as streams,
    sum(streams_change) as streams_change,
    sum(case when chart_rank <= 10 then streams else 0 end)::numeric / nullif(sum(streams), 0) as top_10_stream_share,
    avg(case when is_collaboration then 1.0 else 0.0 end) as collaboration_share,
    avg(case when is_explicit then 1.0 else 0.0 end) as explicit_share,
    avg(days_on_chart) as avg_days_on_chart
from filtered_songs
```

```sql action_segments
with filtered_songs as (
    select
        *,
        case
            when rank_change > 0 and streams_change > 0 and chart_rank <= 50 then 'Accelerare'
            when chart_rank <= 20 and (streams_change < 0 or rank_change < 0) then 'Difendere'
            when days_on_chart >= 30 and streams_change > 0 then 'Estendere'
            when streams_change < 0 and rank_change < 0 then 'Ridurre rischio'
            else 'Mantenere'
        end as action_label
    from spotify_public.mart_top_songs_italy
    where
        ('${inputs.rank_scope.value}' = 'All' or rank_bucket = '${inputs.rank_scope.value}')
        and streams >= cast('${inputs.min_streams.value}' as integer)
        and (
            '${inputs.collab_scope.value}' = 'All'
            or ('${inputs.collab_scope.value}' = 'Collaborazioni' and is_collaboration)
            or ('${inputs.collab_scope.value}' = 'Solo artist' and not is_collaboration)
        )
        and (
            '${inputs.release_scope.value}' = 'All'
            or ('${inputs.release_scope.value}' = 'Fresh' and days_since_release <= 60)
            or ('${inputs.release_scope.value}' = 'Developing' and days_since_release between 61 and 180)
            or ('${inputs.release_scope.value}' = 'Catalog' and days_since_release > 180)
        )
)
select
    action_label,
    count(*) as tracks,
    sum(streams) as streams,
    sum(streams_change) as streams_change,
    avg(chart_rank) as avg_rank
from filtered_songs
group by 1
order by
    case action_label
        when 'Accelerare' then 1
        when 'Difendere' then 2
        when 'Estendere' then 3
        when 'Ridurre rischio' then 4
        else 5
    end
```

```sql momentum_matrix
with filtered_songs as (
    select
        *,
        case
            when rank_change > 0 then 'Rank up'
            when rank_change < 0 then 'Rank down'
            else 'Rank stable'
        end as rank_momentum,
        case
            when streams_change > 0 then 'Streams up'
            when streams_change < 0 then 'Streams down'
            else 'Streams stable'
        end as streams_momentum
    from spotify_public.mart_top_songs_italy
    where
        ('${inputs.rank_scope.value}' = 'All' or rank_bucket = '${inputs.rank_scope.value}')
        and streams >= cast('${inputs.min_streams.value}' as integer)
        and (
            '${inputs.collab_scope.value}' = 'All'
            or ('${inputs.collab_scope.value}' = 'Collaborazioni' and is_collaboration)
            or ('${inputs.collab_scope.value}' = 'Solo artist' and not is_collaboration)
        )
        and (
            '${inputs.release_scope.value}' = 'All'
            or ('${inputs.release_scope.value}' = 'Fresh' and days_since_release <= 60)
            or ('${inputs.release_scope.value}' = 'Developing' and days_since_release between 61 and 180)
            or ('${inputs.release_scope.value}' = 'Catalog' and days_since_release > 180)
        )
)
select
    rank_momentum,
    streams_momentum,
    count(*) as tracks,
    sum(streams) as streams,
    sum(streams_change) as streams_change
from filtered_songs
group by 1, 2
order by streams desc
```

```sql artist_concentration
with filtered_songs as (
    select *
    from spotify_public.mart_top_songs_italy
    where
        ('${inputs.rank_scope.value}' = 'All' or rank_bucket = '${inputs.rank_scope.value}')
        and streams >= cast('${inputs.min_streams.value}' as integer)
        and (
            '${inputs.collab_scope.value}' = 'All'
            or ('${inputs.collab_scope.value}' = 'Collaborazioni' and is_collaboration)
            or ('${inputs.collab_scope.value}' = 'Solo artist' and not is_collaboration)
        )
        and (
            '${inputs.release_scope.value}' = 'All'
            or ('${inputs.release_scope.value}' = 'Fresh' and days_since_release <= 60)
            or ('${inputs.release_scope.value}' = 'Developing' and days_since_release between 61 and 180)
            or ('${inputs.release_scope.value}' = 'Catalog' and days_since_release > 180)
        )
)
select
    artist_names_text as artist_cluster,
    count(*) as tracks,
    sum(streams) as streams,
    avg(chart_rank) as avg_rank,
    min(chart_rank) as best_rank
from filtered_songs
group by 1
order by streams desc
limit 15
```

```sql opportunity_pipeline
with filtered_songs as (
    select
        *,
        case
            when rank_change > 0 and streams_change > 0 and chart_rank <= 50 then 'Accelerare paid/social'
            when chart_rank <= 20 and (streams_change < 0 or rank_change < 0) then 'Difendere playlist e contenuti'
            when days_on_chart >= 30 and streams_change > 0 then 'Estendere radio/editorial'
            when streams_change < 0 and rank_change < 0 then 'Ridurre rischio churn'
            else 'Monitorare'
        end as recommended_action,
        case
            when rank_change > 0 and streams_change > 0 and chart_rank <= 50 then 1
            when chart_rank <= 20 and (streams_change < 0 or rank_change < 0) then 2
            when days_on_chart >= 30 and streams_change > 0 then 3
            when streams_change < 0 and rank_change < 0 then 4
            else 5
        end as action_priority,
        abs(streams_change) as abs_streams_change
    from spotify_public.mart_top_songs_italy
    where
        ('${inputs.rank_scope.value}' = 'All' or rank_bucket = '${inputs.rank_scope.value}')
        and streams >= cast('${inputs.min_streams.value}' as integer)
        and (
            '${inputs.collab_scope.value}' = 'All'
            or ('${inputs.collab_scope.value}' = 'Collaborazioni' and is_collaboration)
            or ('${inputs.collab_scope.value}' = 'Solo artist' and not is_collaboration)
        )
        and (
            '${inputs.release_scope.value}' = 'All'
            or ('${inputs.release_scope.value}' = 'Fresh' and days_since_release <= 60)
            or ('${inputs.release_scope.value}' = 'Developing' and days_since_release between 61 and 180)
            or ('${inputs.release_scope.value}' = 'Catalog' and days_since_release > 180)
        )
)
select
    chart_rank,
    track_name,
    artist_names_text,
    streams,
    streams_change,
    rank_change,
    days_on_chart,
    peak_rank,
    recommended_action,
    action_priority,
    abs_streams_change,
    spotify_track_url
from filtered_songs
order by action_priority, abs_streams_change desc, streams desc
limit 20
```

```sql lifecycle_scatter
with filtered_songs as (
    select
        *,
        case
            when rank_change > 0 and streams_change > 0 and chart_rank <= 50 then 'Accelerare'
            when chart_rank <= 20 and (streams_change < 0 or rank_change < 0) then 'Difendere'
            when days_on_chart >= 30 and streams_change > 0 then 'Estendere'
            when streams_change < 0 and rank_change < 0 then 'Ridurre rischio'
            else 'Mantenere'
        end as action_label,
        abs(streams_change) + 1 as movement_size
    from spotify_public.mart_top_songs_italy
    where
        ('${inputs.rank_scope.value}' = 'All' or rank_bucket = '${inputs.rank_scope.value}')
        and streams >= cast('${inputs.min_streams.value}' as integer)
        and (
            '${inputs.collab_scope.value}' = 'All'
            or ('${inputs.collab_scope.value}' = 'Collaborazioni' and is_collaboration)
            or ('${inputs.collab_scope.value}' = 'Solo artist' and not is_collaboration)
        )
        and (
            '${inputs.release_scope.value}' = 'All'
            or ('${inputs.release_scope.value}' = 'Fresh' and days_since_release <= 60)
            or ('${inputs.release_scope.value}' = 'Developing' and days_since_release between 61 and 180)
            or ('${inputs.release_scope.value}' = 'Catalog' and days_since_release > 180)
        )
)
select
    track_name,
    artist_names_text,
    days_on_chart,
    streams,
    movement_size,
    action_label
from filtered_songs
order by streams desc
limit 80
```

```sql rank_distribution
with filtered_songs as (
    select *
    from spotify_public.mart_top_songs_italy
    where
        ('${inputs.rank_scope.value}' = 'All' or rank_bucket = '${inputs.rank_scope.value}')
        and streams >= cast('${inputs.min_streams.value}' as integer)
        and (
            '${inputs.collab_scope.value}' = 'All'
            or ('${inputs.collab_scope.value}' = 'Collaborazioni' and is_collaboration)
            or ('${inputs.collab_scope.value}' = 'Solo artist' and not is_collaboration)
        )
        and (
            '${inputs.release_scope.value}' = 'All'
            or ('${inputs.release_scope.value}' = 'Fresh' and days_since_release <= 60)
            or ('${inputs.release_scope.value}' = 'Developing' and days_since_release between 61 and 180)
            or ('${inputs.release_scope.value}' = 'Catalog' and days_since_release > 180)
        )
)
select
    rank_bucket,
    count(*) as tracks,
    sum(streams) as streams
from filtered_songs
group by 1
order by
    case rank_bucket
        when 'Top 10' then 1
        when 'Top 50' then 2
        when 'Top 100' then 3
        else 4
    end
```

```sql release_mix
with filtered_songs as (
    select *
    from spotify_public.mart_top_songs_italy
    where
        ('${inputs.rank_scope.value}' = 'All' or rank_bucket = '${inputs.rank_scope.value}')
        and streams >= cast('${inputs.min_streams.value}' as integer)
        and (
            '${inputs.collab_scope.value}' = 'All'
            or ('${inputs.collab_scope.value}' = 'Collaborazioni' and is_collaboration)
            or ('${inputs.collab_scope.value}' = 'Solo artist' and not is_collaboration)
        )
        and (
            '${inputs.release_scope.value}' = 'All'
            or ('${inputs.release_scope.value}' = 'Fresh' and days_since_release <= 60)
            or ('${inputs.release_scope.value}' = 'Developing' and days_since_release between 61 and 180)
            or ('${inputs.release_scope.value}' = 'Catalog' and days_since_release > 180)
        )
)
select
    case
        when days_since_release <= 60 then 'Fresh <=60g'
        when days_since_release <= 180 then 'Developing 61-180g'
        else 'Catalog >180g'
    end as release_stage,
    count(*) as tracks,
    sum(streams) as streams,
    avg(streams_change) as avg_streams_change
from filtered_songs
group by 1
order by
    case release_stage
        when 'Fresh <=60g' then 1
        when 'Developing 61-180g' then 2
        else 3
    end
```

```sql collaboration_mix
with filtered_songs as (
    select *
    from spotify_public.mart_top_songs_italy
    where
        ('${inputs.rank_scope.value}' = 'All' or rank_bucket = '${inputs.rank_scope.value}')
        and streams >= cast('${inputs.min_streams.value}' as integer)
        and (
            '${inputs.collab_scope.value}' = 'All'
            or ('${inputs.collab_scope.value}' = 'Collaborazioni' and is_collaboration)
            or ('${inputs.collab_scope.value}' = 'Solo artist' and not is_collaboration)
        )
        and (
            '${inputs.release_scope.value}' = 'All'
            or ('${inputs.release_scope.value}' = 'Fresh' and days_since_release <= 60)
            or ('${inputs.release_scope.value}' = 'Developing' and days_since_release between 61 and 180)
            or ('${inputs.release_scope.value}' = 'Catalog' and days_since_release > 180)
        )
)
select
    case when is_collaboration then 'Collaborazioni' else 'Solo artist' end as collaboration_type,
    count(*) as tracks,
    sum(streams) as streams,
    avg(streams_change) as avg_streams_change
from filtered_songs
group by 1
order by streams desc
```

# Spotify Italy Analytics

Dashboard decisionale sulla classifica italiana Spotify. I filtri aggiornano KPI, grafici e pipeline di azione per rispondere a tre domande: dove spingere, cosa difendere, e quali pattern replicare.

<div class="grid grid-cols-1 md:grid-cols-4 gap-4">
  <Dropdown name="rank_scope" title="Fascia rank" defaultValue="All">
    <DropdownOption value="All" valueLabel="Tutte" />
    <DropdownOption value="Top 10" />
    <DropdownOption value="Top 50" />
    <DropdownOption value="Top 100" />
    <DropdownOption value="Bottom 100" />
  </Dropdown>

  <Dropdown name="collab_scope" title="Formato artistico" defaultValue="All">
    <DropdownOption value="All" valueLabel="Tutti" />
    <DropdownOption value="Collaborazioni" />
    <DropdownOption value="Solo artist" valueLabel="Solo artist" />
  </Dropdown>

  <ButtonGroup name="release_scope" title="Ciclo release" defaultValue="All">
    <ButtonGroupItem value="All" valueLabel="Tutte" />
    <ButtonGroupItem value="Fresh" valueLabel="Fresh" />
    <ButtonGroupItem value="Developing" valueLabel="Developing" />
    <ButtonGroupItem value="Catalog" valueLabel="Catalog" />
  </ButtonGroup>

  <ButtonGroup name="min_streams" title="Soglia stream" defaultValue="0">
    <ButtonGroupItem value="0" valueLabel="Tutti" />
    <ButtonGroupItem value="100000" valueLabel="100k+" />
    <ButtonGroupItem value="200000" valueLabel="200k+" />
  </ButtonGroup>
</div>

## Stato Del Mercato

<div class="grid grid-cols-1 md:grid-cols-4 gap-4">
  <BigValue data={chart_snapshot} value="tracks" title="Brani filtrati" fmt="num0" />
  <BigValue data={chart_snapshot} value="streams" title="Stream" fmt="num0" />
  <BigValue data={chart_snapshot} value="streams_change" title="Delta stream" fmt="+num0;-num0" />
  <BigValue data={chart_snapshot} value="top_10_stream_share" title="Quota Top 10" fmt="pct1" />
</div>

<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
  <BigValue data={chart_snapshot} value="collaboration_share" title="Quota collaborazioni" fmt="pct1" />
  <BigValue data={chart_snapshot} value="explicit_share" title="Quota explicit" fmt="pct1" />
  <BigValue data={chart_snapshot} value="avg_days_on_chart" title="Giorni medi in chart" fmt="num1" />
</div>

## Dove Agire Ora

<BarChart
  data={action_segments}
  x="action_label"
  y="streams"
  series="action_label"
  yFmt="num0"
  title="Stream per leva di azione"
  subtitle="Segmenta il catalogo filtrato in priorita commerciali"
  sort={false}
  height={340}
/>

<DataTable data={opportunity_pipeline} search>
  <Column id="chart_rank" title="Rank" />
  <Column id="track_name" title="Brano" />
  <Column id="artist_names_text" title="Artisti" />
  <Column id="streams" title="Stream" fmt="num0" contentType="bar" />
  <Column id="streams_change" title="Delta stream" fmt="+num0;-num0" />
  <Column id="rank_change" title="Delta rank" fmt="+num0;-num0" />
  <Column id="days_on_chart" title="Giorni" />
  <Column id="recommended_action" title="Azione suggerita" />
</DataTable>

## Cosa Sta Cambiando

<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
  <BarChart
    data={momentum_matrix}
    x="rank_momentum"
    y="tracks"
    series="streams_momentum"
    yFmt="num0"
    title="Momentum rank vs stream"
    subtitle="Se rank e stream divergono, serve diagnosi prima di aumentare budget"
    sort={false}
    height={340}
  />

  <BubbleChart
    data={lifecycle_scatter}
    x="days_on_chart"
    y="streams"
    size="movement_size"
    series="action_label"
    xFmt="num0"
    yFmt="num0"
    sizeFmt="num0"
    title="Longevita vs intensita"
    subtitle="Bubble piu grandi indicano variazione recente piu alta"
    height={340}
  />
</div>

## Quali Pattern Replicare

<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
  <BarChart
    data={release_mix}
    x="release_stage"
    y="streams"
    yFmt="num0"
    title="Mix per ciclo di release"
    subtitle="Misura se il mercato sta premiando novita o catalogo"
    sort={false}
    height={320}
  />

  <BarChart
    data={collaboration_mix}
    x="collaboration_type"
    y="streams"
    yFmt="num0"
    title="Solo vs collaborazioni"
    subtitle="Usa il filtro formato per isolare il contributo delle collaborazioni"
    sort={false}
    height={320}
  />
</div>

<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
  <BarChart
    data={rank_distribution}
    x="rank_bucket"
    y="streams"
    yFmt="num0"
    title="Concentrazione per fascia rank"
    subtitle="Capisce se gli stream sono catturati dalla testa o distribuiti sulla coda"
    sort={false}
    height={320}
  />

  <BarChart
    data={artist_concentration}
    x="artist_cluster"
    y="streams"
    yFmt="num0"
    title="Artisti e cluster dominanti"
    subtitle="Individua roster o collaborazioni da usare come benchmark"
    sort={false}
    height={320}
  />
</div>

## Lettura Operativa

| Segnale | Come agire |
| --- | --- |
| `Accelerare` con delta stream positivo | Spingere paid social, short-form e pitching playlist finche il momentum e fresco. |
| `Difendere` in Top 20 | Rinforzare contenuti, creator e placement per evitare perdita di share nella testa della chart. |
| `Estendere` con molti giorni in chart | Testare radio, editorial secondarie e contenuti evergreen: il brano ha gia resilienza. |
| `Ridurre rischio` | Controllare cannibalizzazione, uscita competitor e fatigue creativa prima di aumentare budget. |

```sql pipeline_health
select
    chart_date,
    chart_rows,
    matched_tracks,
    match_rate,
    duplicate_tracks,
    missing_streams,
    spotify_retries,
    spotify_429_responses,
    pipeline_status
from spotify_public.mart_data_quality_daily
order by chart_date desc
limit 1
```

```sql history_coverage
select
    min(chart_date) as history_start,
    max(chart_date) as latest_chart_date,
    count(distinct chart_date) as history_days,
    count(*) as observations,
    count(distinct chart_track_id) as distinct_tracks
from spotify_public.fct_track_chart_daily
```

## Affidabilita Della Pipeline

<div class="grid grid-cols-1 md:grid-cols-4 gap-4">
  <BigValue data={pipeline_health} value="chart_rows" title="Righe acquisite" fmt="num0" />
  <BigValue data={pipeline_health} value="match_rate" title="Copertura metadati" fmt="pct1" />
  <BigValue data={history_coverage} value="history_days" title="Giorni di storico" fmt="num0" />
  <BigValue data={pipeline_health} value="pipeline_status" title="Stato pipeline" />
</div>

<DataTable data={pipeline_health}>
  <Column id="chart_date" title="Data chart" />
  <Column id="chart_rows" title="Righe" />
  <Column id="matched_tracks" title="Match Spotify" />
  <Column id="duplicate_tracks" title="Duplicati" />
  <Column id="missing_streams" title="Stream mancanti" />
  <Column id="spotify_retries" title="Retry" />
  <Column id="spotify_429_responses" title="HTTP 429" />
</DataTable>

Lo storico e incrementale e conserva ogni snapshot giornaliero alla grana
`chart_date + country + track_id`. L'obiettivo operativo e superare 90 giorni senza
retrodatare o simulare osservazioni non raccolte.
