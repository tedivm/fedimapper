from datetime import datetime
from typing import Dict

from fedimapper.routers.api.common.schemas.base import ResponseBase


class MetaData(ResponseBase):
    queue_lag_stale: int
    queue_lag_unreachable: int
    unscanned: int
    scanned: int
    last_ingest: datetime | None = None
    sps: float
