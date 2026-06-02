from datetime import datetime
import subprocess

from airflow.sdk import dag, task


@dag(
    dag_id="spotify_extract",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["spotify", "extract", "dlt"],
)
def spotify_extract():
    @task
    def run_dlt_pipeline():
        result = subprocess.run(
            ["python", "spotify_pipeline.py"],
            cwd="/opt/airflow/dlt",
            check=True,
            capture_output=True,
            text=True,
        )
        print(result.stdout)

    run_dlt_pipeline()


spotify_extract()
