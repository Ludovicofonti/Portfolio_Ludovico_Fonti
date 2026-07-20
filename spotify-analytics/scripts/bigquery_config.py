import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BigQueryConfig:
    project: str
    location: str
    raw_dataset: str
    staging_dataset: str
    intermediate_dataset: str
    marts_dataset: str
    maximum_bytes_billed: int

    @classmethod
    def from_env(cls):
        project = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project:
            raise RuntimeError("Set GCP_PROJECT_ID (or GOOGLE_CLOUD_PROJECT) for BigQuery.")
        return cls(
            project=project,
            location=os.getenv("BIGQUERY_LOCATION", "EU"),
            raw_dataset=os.getenv("SPOTIFY_BQ_RAW_DATASET", "spotify_analytics_raw"),
            staging_dataset=os.getenv(
                "SPOTIFY_BQ_STAGING_DATASET", "spotify_analytics_staging"
            ),
            intermediate_dataset=os.getenv(
                "SPOTIFY_BQ_INTERMEDIATE_DATASET", "spotify_analytics_intermediate"
            ),
            marts_dataset=os.getenv("SPOTIFY_BQ_MARTS_DATASET", "spotify_analytics_marts"),
            maximum_bytes_billed=int(os.getenv("BIGQUERY_MAXIMUM_BYTES_BILLED", "10000000000")),
        )

    @property
    def datasets(self):
        return {
            "raw": self.raw_dataset,
            "staging": self.staging_dataset,
            "intermediate": self.intermediate_dataset,
            "marts": self.marts_dataset,
        }
