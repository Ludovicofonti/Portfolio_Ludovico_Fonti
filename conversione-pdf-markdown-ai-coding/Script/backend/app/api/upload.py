import asyncio
import os
import tempfile
from typing import List

import fitz
from fastapi import APIRouter, HTTPException, UploadFile

from app.config import config
from app.models.schemas import UploadResponse
from app.services.job_manager import job_manager, run_conversion
from app.services.ocr_client import check_ollama_available

router = APIRouter()


async def _validate_and_save(file: UploadFile) -> tuple[str, str, int]:
    """Validate a single PDF upload and save to temp file.

    Returns (tmp_path, file_name, file_size).
    Raises HTTPException on validation failure.
    """
    if file.content_type and file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400, detail="Invalid file type. Please upload a PDF file."
        )

    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    if not content[:5] == b"%PDF-":
        raise HTTPException(
            status_code=400, detail="Invalid file type. Please upload a PDF file."
        )

    file_size = len(content)
    if file_size > config.max_file_size_bytes:
        max_mb = config.max_file_size_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=400, detail=f"File too large. Maximum size is {max_mb} MB."
        )

    file_name = file.filename or "upload.pdf"

    tmp_dir = tempfile.gettempdir()
    tmp_path = os.path.join(tmp_dir, f"pdftomd_{os.urandom(8).hex()}.pdf")
    with open(tmp_path, "wb") as f:
        f.write(content)

    try:
        doc = fitz.open(tmp_path)
        is_encrypted = doc.is_encrypted
        page_count = len(doc)
        doc.close()
    except Exception:
        os.unlink(tmp_path)
        raise HTTPException(
            status_code=400, detail="Invalid file type. Please upload a PDF file."
        )

    if is_encrypted:
        os.unlink(tmp_path)
        raise HTTPException(
            status_code=400, detail="Password-protected PDFs are not supported."
        )

    if page_count > config.max_page_count:
        os.unlink(tmp_path)
        raise HTTPException(
            status_code=400,
            detail=f"PDF has too many pages. Maximum is {config.max_page_count} pages.",
        )

    return tmp_path, file_name, file_size


@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_pdf(file: UploadFile | None = None):
    if file is None:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    if not await check_ollama_available():
        raise HTTPException(
            status_code=503,
            detail="OCR service is currently unavailable. Please try again later.",
        )

    tmp_path, file_name, file_size = await _validate_and_save(file)

    job = job_manager.create_job(file_name=file_name, file_size=file_size)
    asyncio.create_task(run_conversion(job.id, tmp_path))

    return UploadResponse(job_id=job.id)


@router.post("/upload/batch", status_code=201)
async def upload_batch(files: List[UploadFile]):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    if not await check_ollama_available():
        raise HTTPException(
            status_code=503,
            detail="OCR service is currently unavailable. Please try again later.",
        )

    job_ids: list[str] = []
    for file in files:
        tmp_path, file_name, file_size = await _validate_and_save(file)
        job = job_manager.create_job(file_name=file_name, file_size=file_size)
        asyncio.create_task(run_conversion(job.id, tmp_path))
        job_ids.append(job.id)

    return {"job_ids": job_ids}
