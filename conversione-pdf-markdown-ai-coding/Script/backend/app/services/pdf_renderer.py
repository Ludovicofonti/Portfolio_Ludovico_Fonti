from __future__ import annotations

import base64
import io

import fitz

from app.config import config


def render_pdf_pages(pdf_path: str) -> list[str]:
    """Render each page of a PDF to a base64-encoded PNG image.

    Returns a list of base64 strings, one per page.
    """
    doc = fitz.open(pdf_path)
    try:
        images: list[str] = []
        scale = config.render_dpi / 72.0
        matrix = fitz.Matrix(scale, scale)
        for page in doc:
            pix = page.get_pixmap(matrix=matrix)
            png_bytes = pix.tobytes("png")
            b64 = base64.b64encode(png_bytes).decode("ascii")
            images.append(b64)
        return images
    finally:
        doc.close()


def get_page_count(pdf_path: str) -> int:
    doc = fitz.open(pdf_path)
    try:
        return len(doc)
    finally:
        doc.close()


def is_encrypted(pdf_path: str) -> bool:
    doc = fitz.open(pdf_path)
    try:
        return doc.is_encrypted
    finally:
        doc.close()
