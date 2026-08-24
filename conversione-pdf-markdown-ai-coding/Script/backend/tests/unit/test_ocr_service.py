import base64

import pytest

from app.config import config
from app.services import ocr_service
from app.services.ocr_client import OCRServiceError


def test_rapidocr_decodes_image_and_returns_markdown(monkeypatch):
    class Result:
        def to_markdown(self):
            return "# Local OCR\n\nPrivate data stays local."

    class Engine:
        def __call__(self, image_bytes):
            assert image_bytes == b"synthetic-png"
            return Result()

    monkeypatch.setattr(ocr_service, "_rapidocr_engine", Engine())
    encoded = base64.b64encode(b"synthetic-png").decode("ascii")

    assert "Private data stays local" in ocr_service._run_rapidocr(encoded)


def test_rapidocr_rejects_empty_output(monkeypatch):
    class Result:
        def to_markdown(self):
            return "   "

    monkeypatch.setattr(ocr_service, "_rapidocr_engine", lambda image: Result())
    encoded = base64.b64encode(b"synthetic-png").decode("ascii")

    with pytest.raises(OCRServiceError, match="no usable text"):
        ocr_service._run_rapidocr(encoded)


@pytest.mark.asyncio
async def test_rapidocr_status_is_local(monkeypatch):
    monkeypatch.setattr(config, "ocr_engine", "rapidocr")

    status = await ocr_service.get_ocr_status()

    assert status.ready
    assert status.model_local
    assert status.privacy_ok
