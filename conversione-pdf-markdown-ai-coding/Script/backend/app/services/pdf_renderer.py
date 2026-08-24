from __future__ import annotations

import base64
import re
from dataclasses import dataclass

import pymupdf as fitz

from app.config import config


@dataclass(frozen=True)
class PDFInspection:
    page_count: int
    ocr_page_numbers: tuple[int, ...]


@dataclass(frozen=True)
class PreparedPage:
    text: str | None
    base64_image: str | None
    extraction_method: str


def _extract_native_text(page: fitz.Page) -> str:
    """Extract readable blocks while preserving a useful paragraph order."""
    parts: list[str] = []
    for block in page.get_text("blocks", sort=True):
        if len(block) >= 7 and block[6] != 0:
            continue
        text = str(block[4]).strip()
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def _meaningful_char_count(text: str) -> int:
    return len(re.sub(r"[^\w]", "", text, flags=re.UNICODE))


def inspect_pdf_bytes(pdf_bytes: bytes) -> PDFInspection:
    """Inspect an in-memory PDF and identify pages that genuinely need OCR."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        if doc.needs_pass or doc.is_encrypted:
            raise PermissionError("Password-protected PDFs are not supported.")
        ocr_pages = tuple(
            page.number + 1
            for page in doc
            if _meaningful_char_count(_extract_native_text(page))
            < config.native_text_min_chars
        )
        return PDFInspection(page_count=len(doc), ocr_page_numbers=ocr_pages)
    finally:
        doc.close()


def prepare_pdf_page(pdf_bytes: bytes, page_index: int) -> PreparedPage:
    """Extract text or render exactly one page, never retaining the whole PDF as images."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        page = doc.load_page(page_index)
        native_text = _extract_native_text(page)
        if _meaningful_char_count(native_text) >= config.native_text_min_chars:
            return PreparedPage(
                text=native_text,
                base64_image=None,
                extraction_method="native",
            )

        scale = config.render_dpi / 72.0
        pix = page.get_pixmap(
            matrix=fitz.Matrix(scale, scale),
            colorspace=fitz.csRGB,
            alpha=False,
        )
        png_bytes = pix.tobytes("png")
        return PreparedPage(
            text=None,
            base64_image=base64.b64encode(png_bytes).decode("ascii"),
            extraction_method="ocr",
        )
    finally:
        doc.close()
