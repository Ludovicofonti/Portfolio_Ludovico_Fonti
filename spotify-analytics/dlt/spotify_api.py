import random
import re
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"
KWORB_ITALY_DAILY_URL = "https://kworb.net/spotify/country/it_daily.html"
SPOTIFY_MAX_RETRIES = 6
SPOTIFY_RETRY_BACKOFF_SECONDS = 2
SPOTIFY_RETRYABLE_STATUS_CODES = {429, 500, 502, 503}


@dataclass
class SpotifyRequestStats:
    requests: int = 0
    retries: int = 0
    rate_limited: int = 0


def raise_for_spotify_error(response):
    if response.ok:
        return

    raise requests.HTTPError(
        f"{response.status_code} error from Spotify: {response.text}",
        response=response,
    )


def _retry_delay(response, attempt, random_fn=random.random):
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after)
                return max(0.0, retry_at.timestamp() - time.time())
            except (TypeError, ValueError, OverflowError):
                pass

    exponential = SPOTIFY_RETRY_BACKOFF_SECONDS * (2**attempt)
    return min(exponential + random_fn(), 90.0)


def get_spotify_with_retry(
    url,
    token,
    params=None,
    max_retries=SPOTIFY_MAX_RETRIES,
    stats=None,
    request_get=requests.get,
    sleep_fn=time.sleep,
    random_fn=random.random,
):
    """Call Spotify with bounded exponential backoff for throttling and 5xx errors."""
    stats = stats or SpotifyRequestStats()
    response = None

    for attempt in range(max_retries + 1):
        stats.requests += 1
        response = request_get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=30,
        )
        if response.status_code not in SPOTIFY_RETRYABLE_STATUS_CODES:
            raise_for_spotify_error(response)
            return response

        if response.status_code == 429:
            stats.rate_limited += 1
        if attempt == max_retries:
            break

        stats.retries += 1
        sleep_fn(_retry_delay(response, attempt, random_fn=random_fn))

    raise_for_spotify_error(response)
    raise RuntimeError("Spotify retry loop completed without a response")


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


def parse_kworb_daily_chart(html):
    """Parse a saved Kworb page without performing network requests."""
    soup = BeautifulSoup(html, "html.parser")
    title_node = soup.select_one(".pagetitle")
    if title_node is None:
        raise ValueError("Kworb chart title is missing")

    title = title_node.get_text(" ", strip=True)
    chart_date_match = re.search(r"Italy - (\d{4}/\d{2}/\d{2})", title)
    if chart_date_match is None:
        raise ValueError(f"Could not extract chart date from title: {title!r}")
    chart_date = chart_date_match.group(1).replace("/", "-")

    table = soup.select_one("table#spotifydaily")
    if table is None:
        raise ValueError("Kworb daily chart table is missing")

    rows = []
    table_rows = table.select("tbody tr") if table.select_one("tbody") else table.select("tr")
    for tr in table_rows:
        cells = tr.select("td")
        if len(cells) < 11:
            continue

        title_cell = cells[2]
        track_link = title_cell.select_one('a[href*="../track/"]')
        artist_links = title_cell.select('a[href*="../artist/"]')
        if not track_link:
            continue

        track_id = track_link["href"].split("/")[-1].replace(".html", "")
        artist_ids = [link["href"].split("/")[-1].replace(".html", "") for link in artist_links]
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

    if not rows:
        raise ValueError("Kworb daily chart contains no parseable rows")
    return rows


def fetch_italy_daily_chart():
    response = requests.get(
        KWORB_ITALY_DAILY_URL,
        headers={"User-Agent": "spotify-analytics-portfolio/1.0"},
        timeout=30,
    )
    response.raise_for_status()
    response.encoding = "utf-8"
    return parse_kworb_daily_chart(response.text)


def get_track_details(token, track_id, market="IT", stats=None, **request_kwargs):
    """Fetch the exact Spotify track referenced by Kworb's canonical Track ID."""
    response = get_spotify_with_retry(
        f"{SPOTIFY_API_BASE_URL}/tracks/{quote(track_id, safe='')}",
        token,
        params={"market": market},
        stats=stats,
        **request_kwargs,
    )
    track = response.json()
    if track.get("id") != track_id:
        raise ValueError(
            f"Spotify returned track {track.get('id')!r} for requested ID {track_id!r}"
        )
    return track


def search_track_details(token, track_name, artist_name, market="IT"):
    """Legacy helper retained for compatibility; new ingestion uses get_track_details."""
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
