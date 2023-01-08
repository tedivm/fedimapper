import os

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from fedimapper.routers.api.common.responses.cached_json import CachedJSONResponse
from fedimapper.routers.api.instances.routes import router as instance_router
from fedimapper.routers.api.meta.routes import router as meta_router
from fedimapper.routers.api.networks.routes import router as networks_router
from fedimapper.routers.api.reputation.routes import router as reputation_router
from fedimapper.routers.api.software.routes import router as software_router
from fedimapper.routers.api.world.routes import router as world_router
from fedimapper.settings import settings
from fedimapper.utils.openapi import deterministic_operation_ids

from . import VERSION

static_file_path = os.path.dirname(os.path.realpath(__file__)) + "/static"

description = f"""
{settings.project_name} exposes a read only API that describes Fediverse Instances and how they relate to each other.

Follow this project on [Github](https://github.com/tedivm/fedimapper/).
"""

app = FastAPI(
    title=settings.project_name,
    version=VERSION,
    description=description,
)

app.mount("/static", StaticFiles(directory=static_file_path), name="static")


app.include_router(world_router, prefix="/api/v1/world", tags=["World"], default_response_class=CachedJSONResponse)


app.include_router(
    software_router, prefix="/api/v1/software", tags=["Software"], default_response_class=CachedJSONResponse
)
app.include_router(
    instance_router, prefix="/api/v1/instances", tags=["Instances"], default_response_class=CachedJSONResponse
)
app.include_router(
    reputation_router, prefix="/api/v1/reputation", tags=["Reputation"], default_response_class=CachedJSONResponse
)
app.include_router(
    networks_router, prefix="/api/v1/networks", tags=["Networks"], default_response_class=CachedJSONResponse
)


app.include_router(meta_router, prefix="/api/v1/meta", tags=["Meta"])

deterministic_operation_ids(app)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse("/docs")
