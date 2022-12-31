from typing import Any

import httpx

from fedimapper.settings import settings

DEFAULT_HEADERS = {"user-agent": settings.crawler_user_agent}


def get(url: str) -> httpx.Response:
    return httpx.get(url, headers=DEFAULT_HEADERS)


def get_json(url: str) -> Any:
    r = httpx.get(url, headers=DEFAULT_HEADERS)
    r.raise_for_status()
    return r.json()
