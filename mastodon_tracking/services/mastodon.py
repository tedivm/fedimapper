import httpx


def get_metadata(host):
    r = httpx.get(f"https://{host}/api/v1/instance")
    r.raise_for_status()
    return r.json()


def get_peers(host):
    r = httpx.get(f"https://{host}/api/v1/instance/peers")
    r.raise_for_status()
    return r.json()


def get_blocked_instances(host):
    r = httpx.get(f"https://{host}/api/v1/instance/domain_blocks")
    r.raise_for_status()
    return r.json()
