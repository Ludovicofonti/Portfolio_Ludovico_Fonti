import tempfile
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.job_manager import job_manager
from app.services.ocr_client import OCRServiceStatus


def _temp_pdf_artifacts() -> set[Path]:
    return set(Path(tempfile.gettempdir()).glob("pdftomd_*.pdf"))


def test_native_pdf_end_to_end_stays_in_memory(text_pdf_bytes):
    before = _temp_pdf_artifacts()

    with TestClient(app) as client:
        upload = client.post(
            "/api/upload",
            files={"file": ("synthetic.pdf", text_pdf_bytes, "application/pdf")},
        )
        assert upload.status_code == 201
        job_id = upload.json()["job_id"]

        deadline = time.monotonic() + 5
        status = None
        while time.monotonic() < deadline:
            status = client.get(f"/api/jobs/{job_id}/status")
            if status.json()["status"] in {"completed", "failed"}:
                break
            time.sleep(0.05)

        assert status.json()["status"] == "completed"
        preview = client.get(f"/api/jobs/{job_id}/preview")
        assert preview.status_code == 200
        assert "LOCAL-TEST-2026" in preview.json()["content"]
        assert preview.headers["cache-control"].startswith("no-store")

        download = client.get(f"/api/jobs/{job_id}/download")
        assert download.status_code == 200
        assert "LOCAL-TEST-2026" in download.text

        deleted = client.delete(f"/api/jobs/{job_id}")
        assert deleted.status_code == 204
        assert client.get(f"/api/jobs/{job_id}/status").status_code == 404

    assert _temp_pdf_artifacts() == before


def test_scanned_pdf_reports_missing_local_model(monkeypatch, scanned_pdf_bytes):
    async def missing_status():
        return OCRServiceStatus(
            available=True,
            model_installed=False,
            model_local=False,
            privacy_ok=True,
            error_message=(
                "Local OCR model 'glm-ocr:q8_0' is not installed. "
                "Run: ollama pull glm-ocr:q8_0"
            ),
        )

    from app.api import upload as upload_api

    monkeypatch.setattr(upload_api, "get_ocr_status", missing_status)
    with TestClient(app) as client:
        response = client.post(
            "/api/upload",
            files={"file": ("scan.pdf", scanned_pdf_bytes, "application/pdf")},
        )
    assert response.status_code == 503
    assert "ollama pull glm-ocr:q8_0" in response.json()["detail"]
    assert job_manager.list_jobs() == []
