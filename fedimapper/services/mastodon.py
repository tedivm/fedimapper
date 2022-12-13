import re

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


class FediVersion:
    software: str
    mastodon_version: str | None = None
    software_version: str | None = None


def get_version_breakdown(version: str) -> FediVersion | None:
    fediversion = FediVersion()

    version_regex = r"^(\d+\.\d+.\d+\S*)"
    version_result = re.search(version_regex, version)
    if not version_result:
        return

    fediversion.mastodon_version = version_result.group(1)

    #
    if "compatible" in version:
        big_regex = r"^(\d+\.\d+.\d+\S*) \(compatible; (\w+) (\d+\.\d+\.*\d*\S*)\)"
        subversion_result = re.search(big_regex, version)
        if subversion_result:
            fediversion.software = subversion_result.group(2)
            fediversion.software_version = subversion_result.group(3)
        else:
            fediversion.software = "unknown"
            fediversion.software_version = "unknown"
    else:
        fediversion.software = "mastodon"
        fediversion.software_version = fediversion.mastodon_version

    return fediversion
