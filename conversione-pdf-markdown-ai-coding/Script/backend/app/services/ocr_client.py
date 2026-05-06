from __future__ import annotations

import httpx

from app.config import config

OCR_PROMPT = (
    "Extract all text from this image as clean markdown with proper "
    "headings, lists, and formatting:"
)


async def ocr_page(base64_image: str) -> str:
    """Send a base64-encoded PNG image to Ollama for OCR and return the text."""
    payload = {
        "model": config.ollama_model,
        "prompt": OCR_PROMPT,
        "images": [base64_image],
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=config.ocr_timeout_seconds) as client:
        resp = await client.post(
            f"{config.ollama_base_url}/api/generate",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "")


async def check_ollama_available() -> bool:
    """Check if Ollama is reachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{config.ollama_base_url}/api/tags")
            return resp.status_code == 200
    except (httpx.HTTPError, Exception):
        return False
