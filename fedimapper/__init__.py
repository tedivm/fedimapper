import logging
import os

from . import _version

__version__ = _version.get_versions()["version"]


logging.basicConfig(level=os.environ.get("LOG_LEVEL", logging.INFO))
