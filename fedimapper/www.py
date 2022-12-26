import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routers.api import stats
from .routers.api.responses.cached_json import CachedJSONResponse

static_file_path = os.path.dirname(os.path.realpath(__file__)) + "/static"

app = FastAPI()

app.mount("/static", StaticFiles(directory=static_file_path), name="static")

app.include_router(stats.router, prefix="/api/v1/stats", default_response_class=CachedJSONResponse)


@app.get("/")
async def root():
    return {"message": "Hello World"}
