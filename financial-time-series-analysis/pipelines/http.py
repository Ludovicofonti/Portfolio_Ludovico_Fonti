"""Client HTTP condiviso con retry, backoff e rispetto di Retry-After."""

from __future__ import annotations

import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

LOGGER = logging.getLogger(__name__)


def retry_session(attempts: int = 5, backoff_seconds: float = 0.5) -> requests.Session:
    retry = Retry(
        total=attempts,
        connect=attempts,
        read=attempts,
        status=attempts,
        backoff_factor=backoff_seconds,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": "financial-ts-platform/0.2"})
    return session


def get_json(session: requests.Session, url: str, *, params: dict, timeout: int = 30):
    try:
        response = session.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        LOGGER.exception("Richiesta fallita: %s params=%s", url, params)
        raise
