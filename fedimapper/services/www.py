import datetime
import json
from threading import Lock
from typing import Any, Tuple
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from cachetools import TTLCache, cached

from fedimapper.settings import settings

DEFAULT_HEADERS = {"user-agent": settings.crawler_user_agent}
DEFAULT_MAX_BYTES = 1024 * 1024 * 4
DEFAULT_MAX_REQUEST_TIME = 10


client = httpx.Client(headers=DEFAULT_HEADERS)


class WWWException(Exception):
    pass


class RobotBlocked(WWWException):
    pass


class SafetyException(WWWException):
    pass


class ExcessivelyLargeRequest(SafetyException):
    pass


class ExcessivelySlowRequest(SafetyException):
    pass


class NoContent(WWWException):
    pass


@cached(cache=TTLCache(maxsize=1024 * 1024 * settings.cache_size_robots, ttl=1800), lock=Lock())
def get_robots(host) -> RobotFileParser:
    rp = RobotFileParser()
    response, contents = get_safe(f"{host}/robots.txt", validate_robots=False)
    if response.status_code in (401, 403):
        rp.disallow_all = True  # type: ignore
    elif response.status_code >= 400 and response.status_code < 500:
        rp.allow_all = True  # type: ignore
    if contents:
        rp.parse(contents.decode("utf-8").splitlines())
    return rp


def url_to_base(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def can_crawl(url: str) -> bool:
    robot = get_robots(url_to_base(url))
    return robot.can_fetch(settings.crawler_user_agent, url)


def get(url: str) -> httpx.Response:
    if not can_crawl(url):
        raise RobotBlocked(f"blocked by robots.txt from crawling {url}")
    return client.get(url, headers=DEFAULT_HEADERS)


def get_safe(
    url: str,
    max_size: int = DEFAULT_MAX_BYTES,
    timeout: float = DEFAULT_MAX_REQUEST_TIME,
    validate_robots: bool = True,
    follow_redirects: bool = False,
) -> Tuple[httpx.Response, bytes | None]:

    if validate_robots and not can_crawl(url):
        raise RobotBlocked(f"blocked by robots.txt from crawling {url}")

    start = datetime.datetime.utcnow()
    with client.stream("GET", url, headers=DEFAULT_HEADERS, follow_redirects=follow_redirects, timeout=timeout) as r:
        if int(r.headers.get("Content-Length", 0)) > max_size:
            return r, None

        data = []
        length = 0
        for chunk in r.iter_bytes():
            data.append(chunk)
            length += len(chunk)
            if length > max_size:
                raise ExcessivelyLargeRequest(f"Request to `{url}` is too large.")
            if (datetime.datetime.utcnow() - start).total_seconds() >= timeout:
                raise ExcessivelySlowRequest(f"Request to `{url}` is too slow.")

        content = b"".join(data)
    return r, content


def get_json(url: str, max_size: int = DEFAULT_MAX_BYTES) -> Any:
    response, content = get_safe(url, max_size)
    response.raise_for_status()
    if not content:
        raise NoContent(f"No content body for {url}")
    return json.loads(content.decode("utf-8"), strict=False)
