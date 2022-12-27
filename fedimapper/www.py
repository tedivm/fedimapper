import os

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .routers.api.common.responses.cached_json import CachedJSONResponse
from .routers.api.instances.routes import router as instance_router
from .routers.api.reputation.routes import router as reputation_router
from .routers.api.software.routes import router as software_router

static_file_path = os.path.dirname(os.path.realpath(__file__)) + "/static"

app = FastAPI()

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


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse("/docs")
