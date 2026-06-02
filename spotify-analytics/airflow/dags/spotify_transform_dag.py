from datetime import datetime
import os
import subprocess

from airflow.sdk import dag, task


@dag(
    dag_id="spotify_transform",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["spotify", "transform", "dbt"],
)
def spotify_transform():
    @task
    def run_dbt_build():
        env = os.environ.copy()
        env["DBT_PROFILES_DIR"] = "/opt/airflow/dbt"

        result = subprocess.run(
            ["dbt", "build"],
            cwd="/opt/airflow/dbt",
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        print(result.stdout)

    run_dbt_build()


spotify_transform()
