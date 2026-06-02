---
title: Spotify Italy Analytics
---

```sql chart_snapshot
select
    max(chart_date) as chart_date,
    count(*) as tracks,
    sum(streams) as streams,
    sum(case when chart_rank <= 10 then streams else 0 end)::numeric / nullif(sum(streams), 0) as top_10_stream_share,
    avg(duration_minutes) as avg_duration_minutes,
    avg(case when is_explicit then 1.0 else 0.0 end) as explicit_share,
    avg(case when is_collaboration then 1.0 else 0.0 end) as collaboration_share
from spotify_public.mart_top_songs_italy
```

```sql top_songs
select
    chart_rank,
    track_name,
    artist_names_text,
    album_name,
    streams,
    streams_share,
    days_on_chart,
    peak_rank,
    rank_change,
    is_explicit,
    is_collaboration,
    album_image_url,
    spotify_track_url
from spotify_public.mart_top_songs_italy
order by chart_rank
limit 25
```

```sql top_artists
select
    artist_stream_rank,
    artist_name,
    track_count,
    streams,
    best_rank,
    average_rank,
    spotify_artist_url
from spotify_public.mart_top_artists_italy
order by artist_stream_rank
limit 15
```

```sql rank_distribution
select
    rank_bucket,
    sum(streams) as streams
from spotify_public.mart_top_songs_italy
group by 1
order by
    case rank_bucket
        when 'Top 10' then 1
        when 'Top 50' then 2
        when 'Top 100' then 3
        else 4
    end
```

```sql momentum
select
    rank_momentum,
    count(*) as tracks,
    sum(streams) as streams
from spotify_public.mart_chart_momentum
group by 1
order by streams desc
```

```sql release_years
select
    release_year,
    count(*) as tracks,
    sum(streams) as streams
from spotify_public.mart_top_songs_italy
where release_year is not null
group by 1
order by release_year desc
limit 12
```

# Spotify Italy Analytics

Snapshot della classifica italiana Spotify. Il report legge gli artefatti CSV pubblici generati dalla pipeline, cosi la stessa dashboard funziona in locale e su GitHub Pages.

<div class="grid grid-cols-1 md:grid-cols-4 gap-4">
  <BigValue data={chart_snapshot} value="tracks" title="Brani in chart" fmt="num0" />
  <BigValue data={chart_snapshot} value="streams" title="Stream Top 200" fmt="num0" />
  <BigValue data={chart_snapshot} value="top_10_stream_share" title="Quota Top 10" fmt="pct1" />
  <BigValue data={chart_snapshot} value="collaboration_share" title="Collaborazioni" fmt="pct1" />
</div>

## Brani Piu Ascoltati

<DataTable data={top_songs} search>
  <Column id="chart_rank" title="Rank" />
  <Column id="track_name" title="Brano" />
  <Column id="artist_names_text" title="Artisti" />
  <Column id="streams" title="Stream" fmt="num0" contentType="bar" />
  <Column id="streams_share" title="Share" fmt="pct2" />
  <Column id="days_on_chart" title="Giorni" />
  <Column id="peak_rank" title="Peak" />
</DataTable>

## Artisti Dominanti

<BarChart
  data={top_artists}
  x="artist_name"
  y="streams"
  yFmt="num0"
  title="Stream per artista"
  subtitle="Somma degli stream dei brani presenti nella Top 200"
  sort={false}
  height={420}
/>

<DataTable data={top_artists}>
  <Column id="artist_stream_rank" title="#" />
  <Column id="artist_name" title="Artista" />
  <Column id="streams" title="Stream" fmt="num0" contentType="bar" />
  <Column id="track_count" title="Brani" fmt="num0" />
  <Column id="best_rank" title="Best rank" fmt="num0" />
  <Column id="average_rank" title="Rank medio" fmt="num1" />
</DataTable>

## Concentrazione E Momentum

<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
  <BarChart
    data={rank_distribution}
    x="rank_bucket"
    y="streams"
    yFmt="num0"
    title="Distribuzione stream per fascia rank"
    sort={false}
    height={320}
  />
  <BarChart
    data={momentum}
    x="rank_momentum"
    y="tracks"
    yFmt="num0"
    title="Brani in salita, discesa o stabili"
    sort={false}
    height={320}
  />
</div>

## Eta Delle Release

<BarChart
  data={release_years}
  x="release_year"
  y="tracks"
  yFmt="num0"
  title="Anno di uscita dei brani in classifica"
  subtitle="Conteggio brani per anno di release"
  sort={false}
  height={360}
/>
