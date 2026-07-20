# BigQuery deployment

BigQuery is the publication warehouse for Spotify Analytics. GitHub Actions remains the
only production scheduler; no Cloud Scheduler, Cloud Run or GCS resources are required.

## Resources created by the daily workflow

The first authenticated run creates these datasets in the existing Google Cloud project:

| Dataset | Purpose |
| --- | --- |
| `spotify_analytics_raw` | Validated Kworb and Spotify snapshots |
| `spotify_analytics_staging` | dbt typed views |
| `spotify_analytics_intermediate` | dbt reusable transformations |
| `spotify_analytics_marts` | Published facts and analytics marts |

The raw loader creates four tables:

- `italy_daily_chart`
- `italy_daily_track_details`
- `italy_daily_track_details__artists`
- `italy_daily_track_details__album__images`

All raw tables are partitioned by `chart_date`, clustered by track/country or artist,
require a partition filter, expire partitions after 365 days and carry the label
`application=spotify-analytics`. dbt creates the staging/intermediate views and all tables
in the marts dataset. Date-grained marts are partitioned and clustered.

## GitHub configuration

Configure these repository variables:

| Variable | Example |
| --- | --- |
| `GCP_PROJECT_ID` | `my-shared-project` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/123456789/locations/global/workloadIdentityPools/github/providers/portfolio` |
| `GCP_SPOTIFY_SERVICE_ACCOUNT` | `spotify-analytics@my-shared-project.iam.gserviceaccount.com` |
| `BIGQUERY_LOCATION` | `EU` |

Keep the existing `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` repository secrets.
No Google service-account key is stored in GitHub.

The service account needs `roles/bigquery.jobUser` on the project and data-editor access
only to the four Spotify datasets. Dataset creation also requires
`bigquery.datasets.create`: grant it for the first bootstrap run (preferably through a
small custom role), then remove it after the datasets exist. The Workload Identity pool
must allow this repository to impersonate only the Spotify service account.

## Cost controls

- `BIGQUERY_MAXIMUM_BYTES_BILLED` defaults to 10 GB per query.
- Raw partitions expire after 365 days.
- Evidence exports are limited to the latest 365 days by default.
- Dataset/table labels isolate Spotify usage in billing reports.
- A GCP budget should be configured as an alert; it is not a hard spending cap.

## Local authenticated run

After configuring Application Default Credentials:

```powershell
$env:GCP_PROJECT_ID = "my-shared-project"
$env:BIGQUERY_LOCATION = "EU"
python scripts/run_public_pipeline.py --skip-extract
```

Without `--skip-extract`, Spotify credentials are also required. The command creates any
missing datasets and raw tables, runs `dbt build --target bigquery`, then exports bounded
CSV artifacts for Evidence.
