from spotify_api import fetch_italy_daily_chart, get_access_token, get_track_details

import dlt


@dlt.source
def spotify_source(client_id, client_secret):
    @dlt.resource(
        write_disposition="merge",
        primary_key=("chart_date", "country", "track_id"),
    )
    def italy_daily_chart():
        yield from fetch_italy_daily_chart()

    @dlt.resource(
        write_disposition="merge",
        primary_key=("chart_date", "chart_country", "chart_track_id"),
    )
    def italy_daily_track_details():
        chart_rows = fetch_italy_daily_chart()
        token = get_access_token(client_id, client_secret)

        for chart_row in chart_rows:
            track = get_track_details(
                token,
                chart_row["track_id"],
                market=chart_row["country"],
            )
            if not track:
                continue

            track["chart_track_id"] = chart_row["track_id"]
            track["chart_date"] = chart_row["chart_date"]
            track["chart_country"] = chart_row["country"]
            track["chart_rank"] = chart_row["rank"]
            track["chart_track_name"] = chart_row["track_name"]
            track["chart_artist_names_text"] = chart_row["artist_names_text"]
            track["chart_streams"] = chart_row["streams"]
            track["chart_streams_total"] = chart_row["streams_total"]
            yield track

    return italy_daily_chart, italy_daily_track_details
