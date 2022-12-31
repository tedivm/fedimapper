from .www import get_json


def get_metadata(host):
    return get_json(f"https://{host}/api/v1/config")


def get_about(host):
    return get_json(f"https://{host}/api/v1/config/about")


def get_custom_settings(host):
    return get_json(f"https://{host}/api/v1/config/custom")


def get_stats(host):
    return get_json(f"https://{host}/api/v1/server/stats")


def get_peers(host):
    return get_json(f"https://{host}/api/v1/server/followers")
