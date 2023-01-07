from typing import List

from .base import ResponseBase


class InstanceList(ResponseBase):
    instances: List[str]
