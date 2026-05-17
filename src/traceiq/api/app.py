import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from traceiq.api.routes import router
from traceiq.api.pipeline import get_cache

@asynccontextmanager
async def lifespan(app: FastAPI):
    cache = get_cache()
    await cache.init()
    yield

def create_app() -> FastAPI:
    app = FastAPI(title="TraceIQ", lifespan=lifespan)
    app.include_router(router)

    frontend_dist = os.path.join(os.path.dirname(__file__), "../../../frontend/dist")
    if os.path.isdir(frontend_dist):
        app.mount("/assets", StaticFiles(directory=f"{frontend_dist}/assets"), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            return FileResponse(f"{frontend_dist}/index.html")

    return app
