import re
import socket
from typing import Tuple

import cymruwhois
import httpx

from .www import SafetyException, get_safe


def get_ip_from_url(url: str) -> str | bool:
    try:
        return socket.gethostbyname(url)
    except:
        return False


def get_asn_data(ip) -> cymruwhois.asrecord:
    client = cymruwhois.Client()
    return client.lookup(ip)


def can_access_https(host) -> Tuple[bool | httpx.Response, str | None]:
    try:
        # Ignore Robots.txt on this call due to a chicken/egg problem- we need to know
        # if the HTTPS service is accessible before we can pull files from it, and the
        # robots.txt file can't be pulled without access to the service itself.
        response, content = get_safe(f"https://{host}", validate_robots=False, timeout=1.0)

        # Return "unreachable" for specific status codes.
        if 500 <= response.status_code <= 520 or response.status_code == 404:
            return False, None

        if content and len(content) > 0:
            return response, content.decode("utf-8")
        return response, ""

    except (httpx.TransportError, SafetyException) as exc:
        return False, None


ASN_REGEXES = [
    # THE-1984-AS -> THE-1986
    re.compile(r"^(THE-[A-Z\d]*)-(?:A[SP]N?)"),
    #
    # UNI2-AS -> UNI2
    re.compile(r"^([A-Z\d]*)-(?:A[SP]N?)"),
    #
    # ALIBABA-CN-NET -> ALIBABA
    re.compile(r"^([A-Z\d]*)-CN-NET"),
    #
    # HETZNER-AS -> HETZNER
    # HETZNER-CLOUD3-AS -> HETZNER-CLOUD
    re.compile(r"^([A-Z-]*)\d*-(?:A[SP]N?)"),
    #
    # ORACLE-BMC-31898 - ORACLE-BMC
    re.compile(r"^([A-Z-]*)-\d+"),
    #
    # AS-CHOOPA -> CHOOPA
    re.compile(r"^AS-([A-Z]*), [A-Z]{2}"),
    #
    # All Caps no spaces or punctuation.
    re.compile(r"^([A-Z]*), [A-Z]{2}"),
]


def clean_asn_company(company: str) -> str:

    if company.startswith("LEASEWEB"):
        return "LEASEWEB"

    for PATTERN in ASN_REGEXES:
        if results := PATTERN.search(company):
            return results.group(1)

    # Remove country postfix
    company = company[:-4]

    company_parts = company.split()
    if len(company_parts) < 2:
        return company

    if company_parts[0] == company_parts[0].upper():

        # URL Check
        if company_parts[1] == company_parts[1].lower():
            if "." in company_parts[1]:
                return company_parts[0]

        # Repeats Check
        if len(company_parts[0]) > 4:
            if company_parts[1].upper().startswith(company_parts[0]):
                return company_parts[0]

    return company
