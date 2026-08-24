import asyncio
import os
import re
from dataclasses import dataclass
from typing import List

import pymupdf as fitz
from fastapi import APIRouter, HTTPException, UploadFile

from app.config import config
from app.models.schemas import UploadResponse
from app.services.job_manager import job_manager, start_conversion
from app.services.ocr_service import get_ocr_status
from app.services.pdf_renderer import PDFInspection, inspect_pdf_bytes

router = APIRouter()


@dataclass(frozen=True)
class ValidatedPDF:
    content: bytes
    file_name: str
    file_size: int
    inspection: PDFInspection


def _safe_file_name(file_name: str | None) -> str:
    name = os.path.basename(file_name or "upload.pdf")
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()
    return name or "upload.pdf"


def _read_pdf_metadata(content: bytes) -> int:
    doc = fitz.open(stream=content, filetype="pdf")
    try:
        if doc.needs_pass or doc.is_encrypted:
            raise PermissionError("Password-protected PDFs are not supported.")
        return len(doc)
    finally:
        doc.close()


async def _validate_and_read(file: UploadFile) -> ValidatedPDF:
    """Validate a PDF while keeping its bytes exclusively in process memory."""
    accepted_content_types = {"application/pdf", "application/octet-stream"}
    if file.content_type and file.content_type not in accepted_content_types:
        raise HTTPException(
            status_code=400, detail="Invalid file type. Please upload a PDF file."
        )

    content = await file.read(config.max_file_size_bytes + 1)
    if not content:
        raise HTTPException(status_code=400, detail="No file uploaded.")
    if len(content) > config.max_file_size_bytes:
        max_mb = config.max_file_size_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=400, detail=f"File too large. Maximum size is {max_mb} MB."
        )
    if content[:5] != b"%PDF-":
        raise HTTPException(
            status_code=400, detail="Invalid file type. Please upload a PDF file."
        )

    try:
        page_count = await asyncio.to_thread(_read_pdf_metadata, content)
    except PermissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail="Invalid or corrupted PDF file."
        ) from exc

    if page_count < 1:
        raise HTTPException(status_code=400, detail="The PDF contains no pages.")
    if page_count > config.max_page_count:
        raise HTTPException(
            status_code=400,
            detail=f"PDF has too many pages. Maximum is {config.max_page_count} pages.",
        )

    inspection = await asyncio.to_thread(inspect_pdf_bytes, content)
    return ValidatedPDF(
        content=content,
        file_name=_safe_file_name(file.filename),
        file_size=len(content),
        inspection=inspection,
    )


async def _require_local_ocr_if_needed(documents: list[ValidatedPDF]) -> None:
    if not any(document.inspection.ocr_page_numbers for document in documents):
        return
    status = await get_ocr_status()
    if not status.ready:
        raise HTTPException(
            status_code=503,
            detail=status.error_message or "Local OCR service is not ready.",
        )


@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_pdf(file: UploadFile | None = None):
    if file is None:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    document = await _validate_and_read(file)
    await _require_local_ocr_if_needed([document])

    job = job_manager.create_job(
        file_name=document.file_name,
        file_size=document.file_size,
        total_pages=document.inspection.page_count,
    )
    start_conversion(job.id, document.content)
    return UploadResponse(job_id=job.id)


@router.post("/upload/batch", status_code=201)
async def upload_batch(files: List[UploadFile]):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")
    if len(files) > config.max_batch_files:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files. Maximum batch size is {config.max_batch_files} files.",
        )

    documents: list[ValidatedPDF] = []
    total_size = 0
    for file in files:
        document = await _validate_and_read(file)
        documents.append(document)
        total_size += document.file_size
        if total_size > config.max_batch_size_bytes:
            max_mb = config.max_batch_size_bytes // (1024 * 1024)
            raise HTTPException(
                status_code=400,
                detail=f"Batch is too large. Maximum total size is {max_mb} MB.",
            )

    # Validate every file before starting any job, avoiding partial batches.
    await _require_local_ocr_if_needed(documents)

    job_ids: list[str] = []
    for document in documents:
        job = job_manager.create_job(
            file_name=document.file_name,
            file_size=document.file_size,
            total_pages=document.inspection.page_count,
        )
        start_conversion(job.id, document.content)
        job_ids.append(job.id)

    return {"job_ids": job_ids}
