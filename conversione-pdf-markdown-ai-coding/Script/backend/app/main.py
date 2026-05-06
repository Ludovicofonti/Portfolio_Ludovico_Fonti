import asyncio
import logging
import pathlib

import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import download, status, upload
from app.config import config
from app.models.schemas import HealthResponse
from app.services.job_manager import job_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def _cleanup_loop():
    """Periodically remove expired completed/failed jobs."""
    while True:
        await asyncio.sleep(60)
        removed = job_manager.cleanup_expired(config.job_ttl_seconds)
        if removed > 0:
            logger.info("Cleaned up %d expired jobs", removed)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_cleanup_loop())
    logger.info("PDF to Markdown server started")
    yield
    task.cancel()


app = FastAPI(title="PDF to Markdown Converter", lifespan=lifespan)

FRONTEND_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "frontend"

app.include_router(upload.router, prefix="/api")
app.include_router(status.router, prefix="/api")
app.include_router(download.router, prefix="/api")

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    ollama_available = False
    ollama_model_loaded = False

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{config.ollama_base_url}/api/tags")
            if resp.status_code == 200:
                ollama_available = True
                data = resp.json()
                models = data.get("models", [])
                ollama_model_loaded = any(
                    m.get("name", "").startswith(config.ollama_model)
                    for m in models
                )
    except (httpx.HTTPError, Exception):
        pass

    status_str = "healthy" if ollama_available and ollama_model_loaded else "degraded"
    return HealthResponse(
        status=status_str,
        ollama_available=ollama_available,
        ollama_model_loaded=ollama_model_loaded,
        model=config.ollama_model,
    )
