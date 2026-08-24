from __future__ import annotations

import enum
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class JobStatus(str, enum.Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class PageContent(BaseModel):
    page_number: int
    text: str
    extraction_method: str = "unknown"
    confidence_warning: str | None = None


class MarkdownResult(BaseModel):
    content: str
    page_contents: list[PageContent]
    output_file_name: str
    native_pages: int = 0
    ocr_pages: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConversionJob(BaseModel):
    id: str
    status: JobStatus = JobStatus.queued
    file_name: str
    file_size: int
    total_pages: int = 0
    current_page: int = 0
    active_page: int = 0
    stage: str = "queued"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    error_message: str | None = None
    result: MarkdownResult | None = None


class UploadResponse(BaseModel):
    job_id: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    file_name: str
    current_page: int
    total_pages: int
    active_page: int
    stage: str
    created_at: datetime
    completed_at: datetime | None = None
    output_file_name: str | None = None
    error_message: str | None = None


class PreviewResponse(BaseModel):
    job_id: str
    file_name: str
    output_file_name: str
    content: str
    page_count: int
    confidence_warnings: list[dict]


class HealthResponse(BaseModel):
    status: str
    ocr_engine: str
    ocr_available: bool
    ocr_model_loaded: bool
    ocr_local: bool
    privacy_mode: str
    error_message: str | None = None
    model: str
