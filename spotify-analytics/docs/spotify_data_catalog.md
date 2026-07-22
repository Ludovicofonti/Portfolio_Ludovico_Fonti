# Spotify Analytics Data Catalog

This catalog documents the production data path behind the Spotify Italy Analytics
Looker Studio report. It describes source ownership, BigQuery layers, model grains and
the controls that prevent incomplete data from reaching the reporting views.

## Production lineage

```text
Kworb Italy Top 200 + Spotify Web API
  -> Python validation and deterministic Track ID enrichment
  -> BigQuery raw tables
  -> dbt staging and intermediate views
  -> dbt facts and analytics marts
  -> BigQuery rpt_* reporting views
  -> Looker Studio
```

GitHub Actions is the production scheduler. BigQuery is both the analytical warehouse
and the publication source. PostgreSQL is used only by the optional local Airflow/dlt
engineering lab.

## Sources

| Source | Data used | Collection rule |
| --- | --- | --- |
| [Kworb Spotify Italy Daily](https://kworb.net/spotify/country/it_daily.html) | Daily rank, streams, chart movement and Spotify Track ID | One observed Top 200 snapshot per successful run |
| [Spotify Web API: Get Track](https://developer.spotify.com/documentation/web-api/reference/get-track) | Track, artist, album, release, duration, explicit flag, artwork and Spotify links | Exact `GET /tracks/{id}` enrichment using the chart Track ID |

Kworb is identified transparently as a public chart mirror. Spotify metadata is cached
and fetched with bounded retries. The project does not use Spotify content to train AI
or machine-learning models.

## BigQuery datasets

Dataset names can be overridden through environment variables; the defaults are:

| Dataset | Materialization | Owner |
| --- | --- | --- |
| `spotify_analytics_raw` | Partitioned source tables | Python loader |
| `spotify_analytics_staging` | Typed views | dbt |
| `spotify_analytics_intermediate` | Reusable enrichment views | dbt |
| `spotify_analytics_marts` | Facts, marts and `rpt_*` views | dbt |

All resources carry the `application=spotify-analytics` label. Raw partitions expire
after 365 days, and date-grained marts require partition filters to limit accidental
full-table scans.

## Raw tables

| Table | Grain | Stable key |
| --- | --- | --- |
| `italy_daily_chart` | One chart position per date, country and track | `chart_date`, `country`, `track_id` |
| `italy_daily_track_details` | One Spotify enrichment per observed chart row | `chart_date`, `chart_track_id` |
| `italy_daily_track_details__artists` | One artist per enriched track | Parent row ID, artist ID and list position |
| `italy_daily_track_details__album__images` | One artwork per enriched track | Parent row ID and list position |

The loader generates deterministic `_dlt_id` values, replaces only incoming
partitions and refuses empty datasets.

## Core analytical models

| Model | Grain and purpose |
| --- | --- |
| `fct_track_chart_daily` | Incremental fact at date, country and Spotify Track ID |
| `mart_top_songs_italy` | Daily track rank, streams and metadata |
| `mart_top_artists_italy` | Daily artist streams and rank |
| `mart_album_release_analysis` | Daily album and release performance |
| `mart_chart_momentum` | Rank and stream movement |
| `mart_chart_entries_exits` | Entry and exit events |
| `mart_track_lifecycle` | Observed peak, persistence and lifecycle state |
| `mart_artist_market_share` | Daily artist share of Top 200 streams |
| `mart_release_cohorts` | Performance grouped by release month |
| `mart_chart_concentration` | Top 10 and Top 50 concentration |
| `mart_data_quality_daily` | Completeness, duplication and metadata coverage |

## Looker Studio reporting views

The report connects to the views below. They keep visualization logic stable and avoid
rebuilding business definitions inside individual charts.

| View | Grain | Primary visualization fields |
| --- | --- | --- |
| `rpt_market_overview_daily` | Date and country | `streams`, `streams_change`, `top_10_stream_share`, `top_50_stream_share`, `collaboration_share`, `explicit_share`, `fresh_streams`, `developing_streams`, `catalog_streams` |
| `rpt_artist_performance_daily` | Date, country and artist | `artist_name`, `track_count`, `streams`, `market_share`, `artist_stream_rank`, `artist_segment` |
| `rpt_track_opportunities_daily` | Date, country and track | `days_on_chart`, `streams`, `movement_size`, `release_stage`, `action_label` |
| `rpt_release_performance_daily` | Date, country and track | Release date, cohort, stage, collaboration and stream fields |
| `rpt_chart_flow_daily` | Observation date and track event | Entry/exit status and track descriptors |
| `rpt_track_lifecycle` | Country and track | Observed dates, peak, streams and lifecycle state |
| `rpt_pipeline_health_daily` | Date and country | Row count, match rate, freshness and history coverage |

The exact mapping between these fields and each visible chart is in the
[dashboard guide](dashboard_guide.md).

## Quality contract

The scheduled run fails before rebuilding the reporting layer when any mandatory
condition fails:

- fewer than 190 chart rows;
- missing dates, ranks, Track IDs or required stream values;
- duplicate chart grains or duplicate daily ranks;
- Spotify metadata coverage below 95%;
- failed dbt model or data tests.

The project also checks rank and stream ranges, non-future dates, lifecycle consistency
and source freshness. Looker Studio remains connected to the last successfully built
BigQuery views if a scheduled refresh fails.

## Known limitations

- History starts with the first collected snapshot; no synthetic backfill is presented
  as observed data.
- Audio features unavailable to newer Spotify applications are excluded.
- Chart continuity depends on the availability of the public mirror and Spotify API.
- Missing or invalid observation dates must be displayed as gaps, not converted into
  zero-stream market events.
- Looker Studio is a presentation layer: reusable business logic remains versioned in
  dbt and BigQuery.
