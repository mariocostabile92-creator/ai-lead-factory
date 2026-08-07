from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi import Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.api.router import api_router
from backend.core.config import settings
from backend.db.session import init_db

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.include_router(api_router, prefix="/api")
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")
init_db()

@app.get("/", include_in_schema=False)
def frontend_home() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)
