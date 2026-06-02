# Spotify Analytics Evidence

Evidence dashboard for the Spotify Italy pipeline.

Public GitHub Pages URL:

```text
https://ludovicofonti.github.io/Portfolio_Ludovico_Fonti/
```

The dashboard reads committed CSV marts from `sources/spotify_public/`. PostgreSQL remains the local warehouse for the dlt and dbt pipeline, but it is not required to serve the public static site.

## Local Docker Run

From `spotify-analytics/`:

```powershell
docker compose run --rm airflow-cli bash -c "cd /opt/airflow && python scripts/refresh_public_data.py"
```

Then start Evidence:

```powershell
docker compose --profile evidence up evidence
```

Open:

```text
http://localhost:3000/Portfolio
```

The compose service keeps `node_modules` in a Docker volume, which avoids slow dependency installs on Windows bind mounts.

## Local NPM Run

Run from `spotify-analytics/evidence/`:

```powershell
npm install
npm run sources
npm run dev
```

## GitHub Pages

The workflow `.github/workflows/spotify-update-data.yml` refreshes the public CSV snapshot, builds Evidence, uploads the Pages artifact, and deploys the dashboard in one run.

The separate `.github/workflows/spotify-deploy-evidence.yml` workflow remains useful when only the Evidence app or page layout changes.
