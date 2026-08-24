import pytest

from app.models.schemas import JobStatus
from app.services.job_manager import job_manager, run_conversion
from app.services.pdf_renderer import inspect_pdf_bytes, prepare_pdf_page
from tests.conftest import make_text_pdf_bytes


def test_inspection_uses_native_text_when_available(text_pdf_bytes):
    inspection = inspect_pdf_bytes(text_pdf_bytes)
    assert inspection.page_count == 1
    assert inspection.ocr_page_numbers == ()

    page = prepare_pdf_page(text_pdf_bytes, 0)
    assert page.extraction_method == "native"
    assert "LOCAL-TEST-2026" in page.text
    assert page.base64_image is None


def test_scanned_page_is_rendered_one_page_at_a_time(scanned_pdf_bytes):
    inspection = inspect_pdf_bytes(scanned_pdf_bytes)
    assert inspection.ocr_page_numbers == (1,)

    page = prepare_pdf_page(scanned_pdf_bytes, 0)
    assert page.extraction_method == "ocr"
    assert page.text is None
    assert page.base64_image


@pytest.mark.asyncio
async def test_native_conversion_completes_without_ocr():
    pdf_bytes = make_text_pdf_bytes(page_count=2)
    job = job_manager.create_job("sample.pdf", len(pdf_bytes), total_pages=2)

    await run_conversion(job.id, pdf_bytes)

    completed = job_manager.get_job(job.id)
    assert completed.status == JobStatus.completed
    assert completed.current_page == 2
    assert completed.result.native_pages == 2
    assert completed.result.ocr_pages == 0
    assert "LOCAL-TEST-2026" in completed.result.content
    assert completed.result.output_file_name == "sample.md"
