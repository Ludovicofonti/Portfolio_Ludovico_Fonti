import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse

from app.models.schemas import JobStatus, JobStatusResponse, PreviewResponse
from app.services.job_manager import cancel_conversion, job_manager

router = APIRouter()


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(job_id: str):
    """Cancel a conversion and immediately remove its in-memory data."""
    if not cancel_conversion(job_id):
        raise HTTPException(status_code=404, detail="Job not found.")
    return Response(status_code=204)


@router.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    resp = JobStatusResponse(
        job_id=job.id,
        status=job.status,
        file_name=job.file_name,
        current_page=job.current_page,
        total_pages=job.total_pages,
        active_page=job.active_page,
        stage=job.stage,
        created_at=job.created_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
    )
    if job.status == JobStatus.completed and job.result:
        resp.output_file_name = job.result.output_file_name
    return resp


@router.get("/jobs/{job_id}/progress")
async def get_job_progress(job_id: str):
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    async def event_stream():
        while True:
            current = job_manager.get_job(job_id)
            if current is None:
                break
            data = {
                "status": current.status.value,
                "current_page": current.current_page,
                "total_pages": current.total_pages,
                "active_page": current.active_page,
                "stage": current.stage,
                "error_message": current.error_message,
            }
            yield f"data: {json.dumps(data)}\n\n"
            if current.status in (JobStatus.completed, JobStatus.failed):
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-store",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/jobs/{job_id}/preview", response_model=PreviewResponse)
async def get_job_preview(job_id: str):
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.status != JobStatus.completed or job.result is None:
        raise HTTPException(status_code=409, detail="Conversion is still in progress.")

    warnings = [
        {"page": pc.page_number, "warning": pc.confidence_warning}
        for pc in job.result.page_contents
        if pc.confidence_warning
    ]

    return PreviewResponse(
        job_id=job.id,
        file_name=job.file_name,
        output_file_name=job.result.output_file_name,
        content=job.result.content,
        page_count=len(job.result.page_contents),
        confidence_warnings=warnings,
    )
