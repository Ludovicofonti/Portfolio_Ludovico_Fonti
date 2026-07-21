# Spotify Analytics Data Catalog

This catalog documents the production data path behind the Spotify Italy Analytics
dashboard. It describes source ownership, BigQuery layers, model grains and the controls
that prevent incomplete data from being published.

## Production lineage

```text
Kworb Italy Top 200 + Spotify Web API
  -> Python validation and deterministic Track ID enrichment
  -> BigQuery raw tables
  -> dbt staging and intermediate views
  -> dbt facts and analytics marts
  -> bounded CSV exports
  -> Evidence on GitHub Pages
```

GitHub Actions is the production scheduler. BigQuery is the publication warehouse;
PostgreSQL is used only by the optional local Airflow/dlt engineering lab.

## Sources

| Source | Data used | Collection rule |
| --- | --- | --- |
| [Kworb Spotify Italy Daily](https://kworb.net/spotify/country/it_daily.html) | Daily rank, streams, chart movement and Spotify Track ID | One observed Top 200 snapshot per run |
| [Spotify Web API: Get Track](https://developer.spotify.com/documentation/web-api/reference/get-track) | Track, artist, album, release, duration, explicit flag, artwork and Spotify links | Exact `GET /tracks/{id}` enrichment using the chart Track ID |

Kworb is identified transparently as a public chart mirror. Spotify metadata is cached
locally and fetched with bounded retries. The project does not use Spotify content to
train AI or machine-learning models.

## BigQuery datasets

Dataset names can be overridden through environment variables; the defaults are:

| Dataset | Materialization | Ownership |
| --- | --- | --- |
| `spotify_analytics_raw` | Partitioned source tables | Python loader |
| `spotify_analytics_staging` | Typed views | dbt |
| `spotify_analytics_intermediate` | Reusable enrichment views | dbt |
| `spotify_analytics_marts` | Facts and analytics tables | dbt |

All resources carry the `application=spotify-analytics` label. Raw partitions expire
after 365 days and date-grained marts require partition filters to limit accidental
full-table scans.

## Raw tables

| Table | Grain | Natural or stable key |
| --- | --- | --- |
| `italy_daily_chart` | One chart position per date, country and track | `chart_date`, `country`, `track_id` |
| `italy_daily_track_details` | One Spotify track enrichment per observed chart row | `chart_date`, `chart_track_id` |
| `italy_daily_track_details__artists` | One artist per enriched track | Parent row ID, artist ID and list position |
| `italy_daily_track_details__album__images` | One artwork image per enriched track | Parent row ID and list position |

The loader generates deterministic `_dlt_id` values, replaces only the incoming
partitions and refuses empty datasets.

## Analytics models

| Model | Grain and purpose |
| --- | --- |
| `fct_track_chart_daily` | Incremental fact at date, country and Spotify Track ID |
| `mart_top_songs_italy` | Song-level daily ranking and metadata |
| `mart_top_artists_italy` | Artist-level daily streams and rank |
| `mart_album_release_analysis` | Album and release-level daily performance |
| `mart_chart_momentum` | Rank and stream movement between observations |
| `mart_chart_entries_exits` | Entry and exit events by observation date |
| `mart_track_lifecycle` | Observed peak, persistence and lifecycle state per track |
| `mart_artist_market_share` | Daily artist share of Top 200 streams |
| `mart_release_cohorts` | Performance grouped by release month |
| `mart_chart_concentration` | Top 10 and Top 50 concentration indicators |
| `mart_data_quality_daily` | Completeness, duplication and metadata coverage status |

## Quality and publication contract

Publication stops when any mandatory condition fails:

- fewer than 190 chart rows;
- missing dates, ranks, Track IDs or stream counts;
- duplicate chart grains or duplicate daily ranks;
- Spotify metadata coverage below 95%;
- empty required marts or failed dbt tests.

The project also checks rank and stream ranges, non-future dates, lifecycle consistency
and source freshness. CSV exports are written atomically, so a failed refresh leaves the
last valid dashboard dataset available.

## Known limitations

- History starts with the first collected snapshot; no synthetic backfill is presented
  as observed data.
- Audio features unavailable to newer Spotify applications are excluded.
- Chart continuity depends on the availability of the public mirror and Spotify API.
- GitHub Pages serves bounded CSV extracts, not direct BigQuery queries.

These constraints are surfaced in the dashboard and data-quality mart rather than hidden
from downstream users.
