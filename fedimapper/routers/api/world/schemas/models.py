from datetime import datetime
from typing import Dict

from fedimapper.routers.api.common.schemas.base import ResponseBase


class WorldData(ResponseBase):
    total_population: int = 0
    active_instances: int = 0
    networks: int = 0
    software: int = 0
    public_ban_lists: int = 0
    public_ban_population: int = 0
    mastodon_compatible_instances: int = 0
