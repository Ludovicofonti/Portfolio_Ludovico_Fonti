# Spotify Analytics Evidence

Evidence dashboard for the Spotify Italy pipeline.

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

The dashboard reads the committed CSV snapshot in `sources/spotify_public/`. PostgreSQL remains the local warehouse for the dlt and dbt pipeline.
