import os

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from fedimapper.routers.api.common.responses.cached_json import CachedJSONResponse
from fedimapper.routers.api.instances.routes import router as instance_router
from fedimapper.routers.api.meta.routes import router as meta_router
from fedimapper.routers.api.reputation.routes import router as reputation_router
from fedimapper.routers.api.software.routes import router as software_router
from fedimapper.utils.openapi import deterministic_operation_ids

from . import VERSION

static_file_path = os.path.dirname(os.path.realpath(__file__)) + "/static"

description = """
Fedimapper exposes a read only API that describes Fediverse Instances and how they relate to each other.
"""

app = FastAPI(
    title="fedimapper",
    version=VERSION,
    description=description,
)

app.mount("/static", StaticFiles(directory=static_file_path), name="static")

app.include_router(
    software_router, prefix="/api/v1/software", tags=["software"], default_response_class=CachedJSONResponse
)
app.include_router(
    instance_router, prefix="/api/v1/instances", tags=["instances"], default_response_class=CachedJSONResponse
)
app.include_router(
    reputation_router, prefix="/api/v1/reputation", tags=["reputation"], default_response_class=CachedJSONResponse
)

app.include_router(meta_router, prefix="/api/v1/meta", tags=["meta"])

deterministic_operation_ids(app)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse("/docs")
