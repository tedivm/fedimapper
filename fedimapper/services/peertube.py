import re

import httpx


def get_metadata(host):
    r = httpx.get(f"https://{host}/api/v1/config")
    r.raise_for_status()
    return r.json()


def get_about(host):
    r = httpx.get(f"https://{host}/api/v1/config/about")
    r.raise_for_status()
    return r.json()


def get_custom_settings(host):
    r = httpx.get(f"https://{host}/api/v1/config/custom")
    r.raise_for_status()
    return r.json()


def get_stats(host):
    r = httpx.get(f"https://{host}/api/v1/server/stats")
    r.raise_for_status()
    return r.json()


def get_peers(host):
    r = httpx.get(f"https://{host}/api/v1/server/followers")
    r.raise_for_status()
    return r.json()
