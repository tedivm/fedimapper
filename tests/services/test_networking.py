import pytest

from fedimapper.services import networking

# ASN-34779   T-                         T-2-AS AS set propagated by T-2 d.o.o., SI
# ASN-3265    XS4ALL-NL Amsterdam        XS4ALL-NL Amsterdam, NL

COMPANY_TESTS = [
    ["TWC", "TWC-11426-CAROLINAS, US"],
    ["UNI2", "UNI2-AS, ES"],
    ["THE-1984", "THE-1984-AS, IS"],
    ["CLOUDFLARE", "CLOUDFLARENET, US"],
    ["CLOUDFLARE", "CLOUDFLARESPECTRUM, US"],
    ["HETZNER", "HETZNER-AS, DE"],
    ["DIGITALOCEAN", "DIGITALOCEAN-ASN, US"],
    ["AKAMAI", "AKAMAI-AP Akamai Technologies, Inc., SG"],
    ["AMAZON", "AMAZON-02, US"],
    ["ORACLE-BMC", "ORACLE-BMC-31898, US"],
    ["COMCAST", "COMCAST-7922, US"],
    ["HETZNER-CLOUD", "HETZNER-CLOUD2-AS, DE"],
    ["HOSTINGER", "AS-HOSTINGER, CY"],
    ["CHOOPA", "AS-CHOOPA, US"],
    ["LEASEWEB", "LEASEWEB-USA-SFO, US"],
    ["LEASEWEB", "LEASEWEB-USA-WDC, US"],
    ["MVPS", "MVPS www.mvps.net, CY"],
    ["DE-WEBGO", "DE-WEBGO www.webgo.de, DE"],
    ["DE-FIRSTCOLO", "DE-FIRSTCOLO www.first-colo.net, DE"],
    ["MYTHIC", "MYTHIC Mythic Beasts Ltd, GB"],
    ["BIGLOBE", "BIGLOBE BIGLOBE Inc., JP"],
    ["ALIBABA", "ALIBABA-CN-NET Alibaba US Technology Co., Ltd., CN"],
    ["MILKYWAN", "MILKYWAN MilkyWan, FR"],
    ["ROUTELABEL", "ASN-ROUTELABEL, NL"],
    ["6NETWORK", "ASN-6NETWORK *** IoT Zrt *** Last-Mile Kft ***, HU"],
]


def test_asn_company_clean():
    for test in COMPANY_TESTS:
        assert networking.clean_asn_company(test[1]) == test[0]
