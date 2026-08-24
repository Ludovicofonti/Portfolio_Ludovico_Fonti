from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone

from app.config import config
from app.models.schemas import ConversionJob, JobStatus, MarkdownResult

logger = logging.getLogger(__name__)


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, ConversionJob] = {}

    def create_job(
        self, file_name: str, file_size: int, total_pages: int = 0
    ) -> ConversionJob:
        job_id = str(uuid.uuid4())
        job = ConversionJob(
            id=job_id,
            file_name=file_name,
            file_size=file_size,
            total_pages=total_pages,
        )
        self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> ConversionJob | None:
        return self._jobs.get(job_id)

    def update_job(self, job_id: str, **kwargs) -> ConversionJob | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        for key, value in kwargs.items():
            setattr(job, key, value)
        return job

    def list_jobs(self) -> list[ConversionJob]:
        return list(self._jobs.values())

    def delete_job(self, job_id: str) -> bool:
        return self._jobs.pop(job_id, None) is not None

    def cleanup_expired(self, ttl_seconds: int) -> int:
        now = datetime.now(timezone.utc)
        expired = [
            jid
            for jid, job in self._jobs.items()
            if job.status in (JobStatus.completed, JobStatus.failed)
            and job.completed_at
            and (now - job.completed_at).total_seconds() > ttl_seconds
        ]
        for jid in expired:
            del self._jobs[jid]
        return len(expired)


job_manager = JobManager()
_conversion_gate = asyncio.Semaphore(max(config.max_concurrent_jobs, 1))
_background_tasks: dict[str, asyncio.Task] = {}


def start_conversion(job_id: str, pdf_bytes: bytes) -> None:
    """Start a tracked background conversion without persisting the PDF to disk."""
    task = asyncio.create_task(run_conversion(job_id, pdf_bytes))
    _background_tasks[job_id] = task
    task.add_done_callback(lambda _task: _background_tasks.pop(job_id, None))


def cancel_conversion(job_id: str) -> bool:
    """Cancel processing and remove all in-memory state for a job."""
    task = _background_tasks.pop(job_id, None)
    if task is not None and not task.done():
        task.cancel()
    return job_manager.delete_job(job_id)


async def run_conversion(job_id: str, pdf_bytes: bytes) -> None:
    """Run the full PDF → Markdown conversion pipeline for a job."""
    from app.services.markdown_assembler import assemble_markdown
    from app.services.ocr_service import ocr_page
    from app.services.pdf_renderer import prepare_pdf_page

    job = job_manager.get_job(job_id)
    if job is None:
        return

    try:
        async with _conversion_gate:
            job_manager.update_job(
                job_id,
                status=JobStatus.processing,
                stage="extracting",
                current_page=0,
                active_page=1 if job.total_pages else 0,
            )

            page_texts: list[str] = []
            extraction_methods: list[str] = []
            for page_index in range(job.total_pages):
                page_number = page_index + 1
                logger.info(
                    "Job %s: processing page %d/%d",
                    job_id,
                    page_number,
                    job.total_pages,
                )
                job_manager.update_job(
                    job_id,
                    stage="extracting",
                    active_page=page_number,
                )
                prepared = await asyncio.to_thread(
                    prepare_pdf_page, pdf_bytes, page_index
                )
                if prepared.extraction_method == "ocr":
                    job_manager.update_job(job_id, stage="ocr")
                    if prepared.base64_image is None:
                        raise RuntimeError("OCR page image was not generated.")
                    text = await ocr_page(prepared.base64_image)
                else:
                    text = prepared.text or ""

                page_texts.append(text)
                extraction_methods.append(prepared.extraction_method)
                job_manager.update_job(
                    job_id,
                    current_page=page_number,
                    active_page=page_number,
                )

            logger.info("Job %s: assembling markdown", job_id)
            job_manager.update_job(job_id, stage="assembling")
            content, page_contents = assemble_markdown(
                page_texts, extraction_methods
            )
            output_name = os.path.splitext(job.file_name)[0] + ".md"

            result = MarkdownResult(
                content=content,
                page_contents=page_contents,
                output_file_name=output_name,
                native_pages=extraction_methods.count("native"),
                ocr_pages=extraction_methods.count("ocr"),
            )

            job_manager.update_job(
                job_id,
                status=JobStatus.completed,
                stage="completed",
                result=result,
                completed_at=datetime.now(timezone.utc),
            )
            logger.info("Job %s: completed successfully", job_id)

    except asyncio.CancelledError:
        job_manager.update_job(
            job_id,
            status=JobStatus.failed,
            stage="failed",
            error_message="Conversion was cancelled.",
            completed_at=datetime.now(timezone.utc),
        )
        raise
    except Exception as exc:
        # Never log document text, OCR payloads or full exception bodies.
        logger.error("Conversion failed for job %s (%s)", job_id, type(exc).__name__)
        job_manager.update_job(
            job_id,
            status=JobStatus.failed,
            stage="failed",
            error_message=str(exc),
            completed_at=datetime.now(timezone.utc),
        )
    finally:
        # Drop the last local reference promptly. Uploaded PDFs never touch disk.
        pdf_bytes = b""
