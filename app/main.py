"""JewelryTryOn FastAPI application."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.db import init_db
from app.routes import create_generation, get_job, list_models, upload_jewelry


ROOT_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = ROOT_DIR / "storage"


@asynccontextmanager
async def lifespan(_: FastAPI):
    STORAGE_DIR.joinpath("uploads").mkdir(parents=True, exist_ok=True)
    STORAGE_DIR.joinpath("results").mkdir(parents=True, exist_ok=True)
    STORAGE_DIR.joinpath("models").mkdir(parents=True, exist_ok=True)
    init_db()
    yield


app = FastAPI(title="JewelryTryOn", lifespan=lifespan)
app.mount("/storage", StaticFiles(directory=STORAGE_DIR), name="storage")

api = APIRouter(prefix="/api")
api.add_api_route("/upload", upload_jewelry, methods=["POST"])
api.add_api_route("/models", list_models, methods=["GET"])
api.add_api_route("/generate", create_generation, methods=["POST"])
api.add_api_route("/jobs/{job_id}", get_job, methods=["GET"])
app.include_router(api)


@app.get("/")
def home() -> FileResponse:
    return FileResponse(ROOT_DIR / "app" / "static" / "index.html")
