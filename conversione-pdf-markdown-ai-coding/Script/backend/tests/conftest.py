from __future__ import annotations

import io

import pymupdf as fitz
import pytest

from app.services.job_manager import job_manager


def _insert_content(page: fitz.Page) -> None:
    page.insert_text((72, 72), "Privacy-first conversion test", fontsize=18)
    page.insert_textbox(
        fitz.Rect(72, 105, 520, 350),
        (
            "Synthetic document with no confidential data.\n"
            "The identifier is LOCAL-TEST-2026.\n"
            "This content must become Markdown locally."
        ),
        fontsize=12,
    )


def make_text_pdf_bytes(page_count: int = 1) -> bytes:
    doc = fitz.open()
    try:
        for _ in range(page_count):
            _insert_content(doc.new_page(width=595, height=842))
        return doc.tobytes()
    finally:
        doc.close()


def make_scanned_pdf_bytes() -> bytes:
    source = fitz.open()
    output = fitz.open()
    try:
        source_page = source.new_page(width=595, height=842)
        _insert_content(source_page)
        image = source_page.get_pixmap(
            matrix=fitz.Matrix(2, 2), alpha=False
        ).tobytes("jpeg")
        output_page = output.new_page(width=595, height=842)
        output_page.insert_image(output_page.rect, stream=image)
        return output.tobytes()
    finally:
        source.close()
        output.close()


@pytest.fixture(autouse=True)
def clear_jobs():
    job_manager._jobs.clear()
    yield
    job_manager._jobs.clear()


@pytest.fixture
def text_pdf_bytes() -> bytes:
    return make_text_pdf_bytes()


@pytest.fixture
def scanned_pdf_bytes() -> bytes:
    return make_scanned_pdf_bytes()
