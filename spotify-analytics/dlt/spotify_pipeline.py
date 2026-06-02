import dlt
from spotify_source import spotify_source

pipeline = dlt.pipeline(
    pipeline_name="spotify",
    destination="postgres",           # dlt ha un connector nativo per Postgres
    dataset_name="spotify_raw",       # schema nel DB
)

source = spotify_source(
    client_id=dlt.secrets["spotify.client_id"],
    client_secret=dlt.secrets["spotify.client_secret"],
)

load_info = pipeline.run(source)
print(load_info)