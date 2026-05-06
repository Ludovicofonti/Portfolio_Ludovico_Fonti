from __future__ import annotations

import enum
from datetime import datetime

from pydantic import BaseModel, Field


class JobStatus(str, enum.Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class PageContent(BaseModel):
    page_number: int
    text: str
    confidence_warning: str | None = None


class MarkdownResult(BaseModel):
    content: str
    page_contents: list[PageContent]
    output_file_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConversionJob(BaseModel):
    id: str
    status: JobStatus = JobStatus.queued
    file_name: str
    file_size: int
    total_pages: int = 0
    current_page: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
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
    ollama_available: bool
    ollama_model_loaded: bool
    model: str
