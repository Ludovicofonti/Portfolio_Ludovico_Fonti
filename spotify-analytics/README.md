# Spotify Italy Analytics

End-to-end analytics project on the Spotify Italy Daily Top 200 chart.

Live dashboard:

```text
https://ludovicofonti.github.io/Portfolio_Ludovico_Fonti/
```

## Business Goal

The project monitors the Italian Spotify chart to understand which songs, artists, albums, and release patterns dominate current listening behavior.

It answers questions such as:

- Which songs are leading the Italian Top 200?
- Which artists aggregate the most daily streams?
- How concentrated are streams in the top ranks?
- Which tracks are gaining or losing momentum?
- Are recent releases dominating the chart?
- How relevant are collaborations and explicit tracks?

## Public Dashboard

The public page is an Evidence static site deployed on GitHub Pages.

Evidence reads versioned CSV marts from:

```text
evidence/sources/spotify_public/
```

The current public URL is:

```text
https://ludovicofonti.github.io/Portfolio_Ludovico_Fonti/
```

## Technical Architecture

Local development demonstrates a complete analytics stack:

```text
Airflow -> dlt -> PostgreSQL -> dbt -> Evidence
```

The public GitHub workflow uses a lighter static path:

```text
GitHub Actions
  -> scripts/refresh_public_data.py
  -> data/raw/
  -> evidence/sources/spotify_public/
  -> Evidence build
  -> GitHub Pages deploy
```

PostgreSQL remains the local warehouse for the technical pipeline. The published dashboard does not depend on the local database.

## Data Sources

- Kworb Spotify Daily Italy chart for rank and stream counts.
- Spotify Web API Search for track, artist, album, release, duration, and explicit metadata.

Known limitation: newer Spotify apps do not have access to several historical audio feature endpoints, so the project focuses on chart behavior, streams, rank movement, release timing, and metadata that are still available.

## Automation

The workflow `.github/workflows/spotify-update-data.yml` runs:

- manually through GitHub Actions;
- automatically every day at `04:30 UTC`.

It validates Spotify secrets, refreshes the latest snapshot, commits changed CSV/raw files, builds Evidence, and deploys GitHub Pages in the same run.

Required repository secrets:

```text
SPOTIFY_CLIENT_ID
SPOTIFY_CLIENT_SECRET
```

## Local Run

From `spotify-analytics/`:

```powershell
docker compose up -d postgres redis airflow-init airflow-webserver airflow-scheduler
docker compose run --rm airflow-cli bash -c "cd /opt/airflow && python scripts/refresh_public_data.py"
docker compose --profile evidence up evidence
```

Open:

```text
http://localhost:3000/Portfolio
```

## Documentation

- Business and technical project narrative: `spotify_pipeline_portfolio.md`
- Data catalog and API limitations: `docs/spotify_data_catalog.md`
- Evidence-specific run notes: `evidence/README.md`
