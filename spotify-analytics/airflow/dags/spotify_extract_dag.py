import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

import psycopg2
from airflow.sdk import dag, task


def spotify_connection():
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "postgres"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        user=os.environ.get("POSTGRES_USER", "airflow"),
        password=os.environ.get("POSTGRES_PASSWORD", "airflow"),
        dbname=os.environ.get("POSTGRES_SPOTIFY_DB", "spotify_db"),
    )


@dag(
    dag_id="spotify_daily_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    tags=["spotify", "dlt", "dbt", "quality"],
)
def spotify_daily_pipeline():
    @task
    def extract():
        result = subprocess.run(
            ["python", "spotify_pipeline.py"],
            cwd="/opt/airflow/dlt",
            check=True,
            capture_output=True,
            text=True,
        )
        print(result.stdout)

    @task
    def validate_raw():
        query = """
            select chart_date, count(*) as chart_rows,
                   count(distinct track_id) as unique_tracks,
                   count(*) filter (
                       where chart_date is null or rank is null or track_id is null
                   ) as incomplete_rows
            from spotify_raw.italy_daily_chart
            where chart_date = (select max(chart_date) from spotify_raw.italy_daily_chart)
            group by chart_date
        """
        with spotify_connection() as connection, connection.cursor() as cursor:
            cursor.execute(query)
            row = cursor.fetchone()
        if row is None or row[1] < 190 or row[1] != row[2] or row[3] > 0:
            raise ValueError(f"Raw chart health gate failed: {row}")
        return {"chart_date": str(row[0]), "chart_rows": row[1]}

    @task
    def dbt_build():
        env = os.environ.copy()
        env["DBT_PROFILES_DIR"] = "/opt/airflow/dbt"
        result = subprocess.run(
            ["dbt", "build", "--target", "dev"],
            cwd="/opt/airflow/dbt",
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        print(result.stdout)

    @task
    def validate_marts(raw_status):
        query = """
            select chart_rows, matched_tracks, match_rate, pipeline_status
            from spotify_marts.mart_data_quality_daily
            where chart_date = %s
        """
        with spotify_connection() as connection, connection.cursor() as cursor:
            cursor.execute(query, (raw_status["chart_date"],))
            row = cursor.fetchone()
        if row is None or row[0] < 190 or row[2] < 0.95 or row[3] != "fresh":
            raise ValueError(f"Mart health gate failed: {row}")
        return {**raw_status, "matched_tracks": row[1], "match_rate": float(row[2])}

    @task
    def publish_metadata(mart_status):
        output = Path("/opt/airflow/data/quality/local_pipeline_status.json")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(
                {
                    **mart_status,
                    "pipeline_status": "fresh",
                    "published_at": datetime.now().astimezone().isoformat(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    raw_status = validate_raw()
    extract_task = extract()
    extract_task >> raw_status
    transform = dbt_build()
    raw_status >> transform
    marts = validate_marts(raw_status)
    transform >> marts
    publish_metadata(marts)


spotify_daily_pipeline()
