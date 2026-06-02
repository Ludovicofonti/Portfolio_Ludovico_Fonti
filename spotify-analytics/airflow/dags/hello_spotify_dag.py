from datetime import datetime

from airflow.sdk import dag, task


@dag(
    dag_id="hello_spotify_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    tags=["spotify", "test"],
)
def hello_spotify_pipeline():

    @task
    def hello():
        print("Airflow is ready for the Spotify pipeline.")

    hello()


hello_spotify_pipeline()
