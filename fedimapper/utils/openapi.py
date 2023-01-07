from fastapi import FastAPI
from fastapi.routing import APIRoute


def deterministic_operation_ids(app: FastAPI) -> None:
    operation_ids = set([])

    for route in app.routes:
        if isinstance(route, APIRoute):
            if route.name in operation_ids:
                raise Exception(f"Multiple routes use the same operation id: {route.name}")
            route.operation_id = route.name
            operation_ids.add(route.name)
