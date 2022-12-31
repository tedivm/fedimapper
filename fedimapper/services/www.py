from threading import Lock
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from cachetools import TTLCache, cached

from fedimapper.settings import settings

DEFAULT_HEADERS = {"user-agent": settings.crawler_user_agent}


class RobotBlocked(Exception):
    pass


@cached(cache=TTLCache(maxsize=1024 * 1024 * settings.cache_size_robots, ttl=1800), lock=Lock())
def get_robots(host) -> RobotFileParser:
    rp = RobotFileParser()
    rp.set_url(f"{host}/robots.txt")
    rp.read()
    return rp


def url_to_base(url: str):
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def can_crawl(url: str) -> bool:
    robot = get_robots(url_to_base(url))
    return robot.can_fetch(settings.crawler_user_agent, url)


def get(url: str) -> httpx.Response:
    if not can_crawl(url):
        raise RobotBlocked(f"blocked by robots.txt from crawling {url}")
    return httpx.get(url, headers=DEFAULT_HEADERS)


def get_json(url: str) -> Any:
    if not can_crawl(url):
        raise RobotBlocked(f"blocked by robots.txt from crawling {url}")
    r = httpx.get(url, headers=DEFAULT_HEADERS)
    r.raise_for_status()
    return r.json()
