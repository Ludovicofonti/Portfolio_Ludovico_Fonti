from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime

from app.models.schemas import ConversionJob, JobStatus, MarkdownResult

logger = logging.getLogger(__name__)


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, ConversionJob] = {}

    def create_job(self, file_name: str, file_size: int) -> ConversionJob:
        job_id = str(uuid.uuid4())
        job = ConversionJob(
            id=job_id,
            file_name=file_name,
            file_size=file_size,
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
        now = datetime.utcnow()
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


async def run_conversion(job_id: str, pdf_path: str) -> None:
    """Run the full PDF → Markdown conversion pipeline for a job."""
    from app.services.markdown_assembler import assemble_markdown
    from app.services.ocr_client import ocr_page
    from app.services.pdf_renderer import render_pdf_pages

    job = job_manager.get_job(job_id)
    if job is None:
        return

    try:
        # Render all pages to images
        logger.info("Job %s: rendering PDF pages", job_id)
        images = render_pdf_pages(pdf_path)
        logger.info("Job %s: rendered %d pages", job_id, len(images))
        job_manager.update_job(
            job_id,
            status=JobStatus.processing,
            total_pages=len(images),
            current_page=0,
        )

        # OCR each page sequentially
        page_texts: list[str] = []
        for i, img_b64 in enumerate(images, start=1):
            logger.info("Job %s: OCR page %d/%d", job_id, i, len(images))
            text = await ocr_page(img_b64)
            page_texts.append(text)
            job_manager.update_job(job_id, current_page=i)

        # Assemble markdown
        logger.info("Job %s: assembling markdown", job_id)
        content, page_contents = assemble_markdown(page_texts)
        output_name = os.path.splitext(job.file_name)[0] + ".md"

        result = MarkdownResult(
            content=content,
            page_contents=page_contents,
            output_file_name=output_name,
        )

        job_manager.update_job(
            job_id,
            status=JobStatus.completed,
            result=result,
            completed_at=datetime.utcnow(),
        )
        logger.info("Job %s: completed successfully", job_id)

    except Exception as exc:
        logger.exception("Conversion failed for job %s", job_id)
        job_manager.update_job(
            job_id,
            status=JobStatus.failed,
            error_message=str(exc),
            completed_at=datetime.utcnow(),
        )
    finally:
        # Clean up temp PDF
        try:
            os.unlink(pdf_path)
        except OSError:
            pass
