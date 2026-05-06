import io
import zipfile
from typing import List

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response, StreamingResponse

from app.models.schemas import JobStatus
from app.services.job_manager import job_manager

router = APIRouter()


@router.get("/jobs/batch/download")
async def download_batch(job_ids: List[str] = Query(...)):
    """Download multiple completed jobs as a ZIP archive."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for job_id in job_ids:
            job = job_manager.get_job(job_id)
            if job is None:
                continue
            if job.status != JobStatus.completed or job.result is None:
                continue
            zf.writestr(job.result.output_file_name, job.result.content)

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="converted.zip"'},
    )


@router.get("/jobs/{job_id}/download")
async def download_markdown(job_id: str):
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.status == JobStatus.failed:
        raise HTTPException(
            status_code=410, detail="Conversion failed. No result available."
        )

    if job.status != JobStatus.completed or job.result is None:
        raise HTTPException(
            status_code=409, detail="Conversion is still in progress."
        )

    return Response(
        content=job.result.content,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{job.result.output_file_name}"'
        },
    )
