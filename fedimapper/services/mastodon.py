import re

from pydantic import BaseModel

from .www import get_json


def get_metadata(host):
    return get_json(f"https://{host}/api/v1/instance")


def get_peers(host):
    return get_json(f"https://{host}/api/v1/instance/peers")


def get_blocked_instances(host):
    return get_json(f"https://{host}/api/v1/instance/domain_blocks")


class FediVersion(BaseModel):
    software: str | None = None
    mastodon_version: str | None = None
    software_version: str | None = None


def owncast_mapper(version: str) -> FediVersion:
    fediversion = FediVersion()
    version_regex = r"^Owncast v(\d+\.\d+\.\d+-?\w*)"
    version_result = re.search(version_regex, version)
    if not version_result:
        return fediversion

    fediversion = FediVersion()
    fediversion.software = "owncast"
    fediversion.software_version = version_result.group(1)
    return fediversion


def takahe_mapper(version: str) -> FediVersion:
    fediversion = FediVersion()
    if not version.startswith("takahe"):
        return fediversion

    fediversion.software = "takahe"
    fediversion.mastodon_version = None
    fediversion.software_version = version.split("/")[1]
    return fediversion


def glitch_mapper(version: str) -> FediVersion:
    fediversion = last_resort_version_breakdown(version)
    fediversion.software = "glitch"
    return fediversion


def hometown_mapper(version: str) -> FediVersion:
    fediversion = last_resort_version_breakdown(version)
    fediversion.software = "hometown"
    if fediversion.software_version:
        fediversion.software_version = fediversion.software_version.split("-")[1]
    if fediversion.mastodon_version:
        fediversion.mastodon_version = fediversion.mastodon_version.split("+")[0]
    return fediversion


VERSION_MAPPER = {
    "owncast": owncast_mapper,
    "takahe": takahe_mapper,
    "glitch": glitch_mapper,
    "hometown": hometown_mapper,
}


def get_version_breakdown(version: str) -> FediVersion:

    for search_string, mapper_function in VERSION_MAPPER.items():
        if search_string.lower() in version:
            return mapper_function(version)
    return last_resort_version_breakdown(version)


def last_resort_version_breakdown(version: str) -> FediVersion:
    fediversion = FediVersion()

    version_regex = r"^(\d+\.\d+.\d+\S*)"
    version_result = re.search(version_regex, version)
    if not version_result:
        return fediversion

    fediversion.mastodon_version = version_result.group(1)

    if "compatible" in version:
        big_regex = r"^(\d+\.\d+.\d+\S*) \(compatible; (\w+) (\d+\.\d+\.*\d*\S*)\)"
        subversion_result = re.search(big_regex, version)
        if subversion_result:
            fediversion.software = subversion_result.group(2).lower()
            fediversion.software_version = subversion_result.group(3)
        else:
            fediversion.software = "unknown"
            fediversion.software_version = "unknown"
    else:
        fediversion.software = "mastodon"
        fediversion.software_version = fediversion.mastodon_version

    return fediversion
