from __future__ import annotations

import asyncio
import base64

from app.config import config
from app.services.ocr_client import (
    OCRServiceError,
    OCRServiceStatus,
    close_ocr_client,
    get_ollama_status,
    ocr_page as ollama_ocr_page,
)

_rapidocr_engine = None


def _get_rapidocr_engine():
    global _rapidocr_engine
    if _rapidocr_engine is None:
        from rapidocr import RapidOCR

        _rapidocr_engine = RapidOCR()
    return _rapidocr_engine


def _run_rapidocr(base64_image: str) -> str:
    """Run bundled ONNX models on bytes in RAM and return layout-aware Markdown."""
    try:
        image_bytes = base64.b64decode(base64_image, validate=True)
        result = _get_rapidocr_engine()(image_bytes)
        markdown = result.to_markdown().strip()
    except OCRServiceError:
        raise
    except Exception as exc:
        raise OCRServiceError("Local RapidOCR processing failed.") from exc
    finally:
        if "image_bytes" in locals():
            image_bytes = b""

    if not markdown:
        raise OCRServiceError("Local RapidOCR returned no usable text.")
    return markdown


async def get_ocr_status() -> OCRServiceStatus:
    if config.ocr_engine == "rapidocr":
        try:
            import onnxruntime  # noqa: F401
            import rapidocr  # noqa: F401
        except ImportError:
            return OCRServiceStatus(
                available=False,
                model_installed=False,
                model_local=True,
                privacy_ok=True,
                error_message=(
                    "RapidOCR is not installed. Run: pip install rapidocr onnxruntime"
                ),
            )
        return OCRServiceStatus(True, True, True, True)

    if config.ocr_engine == "ollama":
        return await get_ollama_status()

    return OCRServiceStatus(
        available=False,
        model_installed=False,
        model_local=False,
        privacy_ok=False,
        error_message="Unsupported OCR_ENGINE. Use 'rapidocr' or 'ollama'.",
    )


async def ocr_page(base64_image: str) -> str:
    if config.ocr_engine == "rapidocr":
        return await asyncio.to_thread(_run_rapidocr, base64_image)
    if config.ocr_engine == "ollama":
        return await ollama_ocr_page(base64_image)
    raise OCRServiceError("Unsupported OCR_ENGINE. Use 'rapidocr' or 'ollama'.")


async def close_ocr_service() -> None:
    global _rapidocr_engine
    await close_ocr_client()
    _rapidocr_engine = None
