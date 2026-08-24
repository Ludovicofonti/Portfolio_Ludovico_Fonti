import asyncio
import contextlib
import logging
import pathlib

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import download, status, upload
from app.config import config
from app.models.schemas import HealthResponse
from app.services.job_manager import job_manager
from app.services.ocr_service import close_ocr_service, get_ocr_status

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
    logger.info("PDF to Markdown server started in privacy-first mode")
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        await close_ocr_service()


app = FastAPI(title="PDF to Markdown Converter", lifespan=lifespan)

FRONTEND_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "frontend"

app.include_router(upload.router, prefix="/api")
app.include_router(status.router, prefix="/api")
app.include_router(download.router, prefix="/api")

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.middleware("http")
async def privacy_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    ocr_status = await get_ocr_status()
    model_name = (
        "RapidOCR / ONNX CPU"
        if config.ocr_engine == "rapidocr"
        else config.ollama_model
    )
    return HealthResponse(
        status="healthy" if ocr_status.ready else "degraded",
        ocr_engine=config.ocr_engine,
        ocr_available=ocr_status.available,
        ocr_model_loaded=ocr_status.model_installed,
        ocr_local=ocr_status.model_local,
        privacy_mode=(
            "remote-opt-in"
            if config.ocr_engine == "ollama" and config.allow_remote_ocr
            else "local-only"
        ),
        error_message=ocr_status.error_message,
        model=model_name,
    )
