import re
import time

import requests
from bs4 import BeautifulSoup


SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"
KWORB_ITALY_DAILY_URL = "https://kworb.net/spotify/country/it_daily.html"
SPOTIFY_MAX_RETRIES = 6
SPOTIFY_RETRY_BACKOFF_SECONDS = 5


def raise_for_spotify_error(response):
    if response.ok:
        return

    raise requests.HTTPError(
        f"{response.status_code} error from Spotify: {response.text}",
        response=response,
    )


def get_spotify_with_retry(url, token, params=None, max_retries=SPOTIFY_MAX_RETRIES):
    for attempt in range(max_retries):
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=30,
        )
        if response.status_code != 429:
            raise_for_spotify_error(response)
            return response

        retry_after = response.headers.get("Retry-After")
        if retry_after and retry_after.isdigit():
            sleep_seconds = int(retry_after)
        else:
            sleep_seconds = SPOTIFY_RETRY_BACKOFF_SECONDS * (attempt + 1)

        time.sleep(min(sleep_seconds, 90))

    raise_for_spotify_error(response)


def get_access_token(client_id, client_secret):
    response = requests.post(
        SPOTIFY_TOKEN_URL,
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
        timeout=30,
    )
    raise_for_spotify_error(response)
    return response.json()["access_token"]


def parse_int(value):
    value = value.strip().replace(",", "").replace("+", "")
    if not value or value in {"-", "="}:
        return None
    return int(value)


def fetch_italy_daily_chart():
    response = requests.get(
        KWORB_ITALY_DAILY_URL,
        headers={"User-Agent": "spotify-analytics-portfolio/1.0"},
        timeout=30,
    )
    response.raise_for_status()
    response.encoding = "utf-8"

    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.select_one(".pagetitle").get_text(" ", strip=True)
    chart_date_match = re.search(r"Italy - (\d{4}/\d{2}/\d{2})", title)
    chart_date = chart_date_match.group(1).replace("/", "-") if chart_date_match else None

    rows = []
    table = soup.select_one("table#spotifydaily")
    for tr in table.select("tbody tr") if table.select_one("tbody") else table.select("tr"):
        cells = tr.select("td")
        if len(cells) < 11:
            continue

        title_cell = cells[2]
        track_link = title_cell.select_one('a[href*="../track/"]')
        artist_links = title_cell.select('a[href*="../artist/"]')

        if not track_link:
            continue

        track_id = track_link["href"].split("/")[-1].replace(".html", "")
        artist_ids = [
            link["href"].split("/")[-1].replace(".html", "")
            for link in artist_links
        ]
        artist_names = [link.get_text(strip=True) for link in artist_links]

        rows.append(
            {
                "chart_date": chart_date,
                "country": "IT",
                "country_name": "Italy",
                "chart_source": "kworb_spotify_daily",
                "rank": parse_int(cells[0].get_text(strip=True)),
                "rank_change": cells[1].get_text(strip=True),
                "track_id": track_id,
                "track_name": track_link.get_text(strip=True),
                "artist_ids": artist_ids,
                "artist_names": artist_names,
                "artist_names_text": ", ".join(artist_names),
                "days_on_chart": parse_int(cells[3].get_text(strip=True)),
                "peak_rank": parse_int(cells[4].get_text(strip=True)),
                "peak_count_text": cells[5].get_text(strip=True),
                "streams": parse_int(cells[6].get_text(strip=True)),
                "streams_change": parse_int(cells[7].get_text(strip=True)),
                "streams_7day": parse_int(cells[8].get_text(strip=True)),
                "streams_7day_change": parse_int(cells[9].get_text(strip=True)),
                "streams_total": parse_int(cells[10].get_text(strip=True)),
                "kworb_track_url": f"https://kworb.net/spotify/track/{track_id}.html",
            }
        )

    return rows


def search_track_details(token, track_name, artist_name, market="IT"):
    response = get_spotify_with_retry(
        f"{SPOTIFY_API_BASE_URL}/search",
        token,
        params={
            "q": f"track:{track_name} artist:{artist_name}",
            "type": "track",
            "market": market,
            "limit": 1,
        },
    )
    items = response.json()["tracks"]["items"]
    return items[0] if items else None
