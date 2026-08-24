from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.config import config

OCR_PROMPT = (
    "Text Recognition: [img-0]\n"
    "Extract all visible text as clean Markdown. "
    "Preserve headings, lists, tables and reading order. Return only Markdown."
)


class OCRServiceError(RuntimeError):
    pass


@dataclass(frozen=True)
class OCRServiceStatus:
    available: bool
    model_installed: bool
    model_local: bool
    privacy_ok: bool
    error_message: str | None = None

    @property
    def ready(self) -> bool:
        return (
            self.available
            and self.model_installed
            and self.privacy_ok
        )


_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        timeout = httpx.Timeout(config.ocr_timeout_seconds, connect=5.0)
        # Ignore proxy environment variables: local document data must not be proxied.
        _client = httpx.AsyncClient(timeout=timeout, trust_env=False)
    return _client


async def close_ocr_client() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


def _model_matches(requested: str, installed: str) -> bool:
    if requested == installed:
        return True
    return ":" not in requested and installed.startswith(f"{requested}:")


def _normalize_ocr_response(response: str) -> str:
    """Remove a single outer Markdown fence and reject content-free OCR output."""
    text = response.strip()
    if text.startswith("```") and text.endswith("```"):
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 : -3].strip()
    if not text:
        raise OCRServiceError(
            "Local OCR returned no usable text. Ollama 0.17.1-0.17.5 has a "
            "known GLM-OCR image regression; update Ollama or keep the [img-0] workaround."
        )
    return text


async def get_ollama_status() -> OCRServiceStatus:
    if not config.remote_ocr_allowed:
        return OCRServiceStatus(
            available=False,
            model_installed=False,
            model_local=False,
            privacy_ok=False,
            error_message=(
                "Remote OCR endpoint blocked by privacy policy. "
                "Use localhost or explicitly set ALLOW_REMOTE_OCR=true."
            ),
        )

    try:
        resp = await _get_client().get(f"{config.ollama_base_url}/api/tags", timeout=5.0)
        resp.raise_for_status()
        models = resp.json().get("models", [])
    except (httpx.HTTPError, ValueError):
        return OCRServiceStatus(
            available=False,
            model_installed=False,
            model_local=False,
            privacy_ok=True,
            error_message="Local Ollama service is unavailable.",
        )

    matches = [
        model
        for model in models
        if _model_matches(config.ollama_model, str(model.get("name", "")))
    ]
    if not matches:
        return OCRServiceStatus(
            available=True,
            model_installed=False,
            model_local=False,
            privacy_ok=True,
            error_message=(
                f"Local OCR model '{config.ollama_model}' is not installed. "
                f"Run: ollama pull {config.ollama_model}"
            ),
        )

    model_local = any(not model.get("remote_host") for model in matches)
    if not model_local and not config.allow_remote_ocr:
        return OCRServiceStatus(
            available=True,
            model_installed=True,
            model_local=False,
            privacy_ok=False,
            error_message="Cloud-hosted Ollama models are blocked by privacy policy.",
        )

    return OCRServiceStatus(
        available=True,
        model_installed=True,
        model_local=model_local,
        privacy_ok=model_local or config.allow_remote_ocr,
    )


async def ocr_page(base64_image: str) -> str:
    """Send one page only to the privacy-approved Ollama endpoint."""
    if not config.remote_ocr_allowed:
        raise OCRServiceError("Remote OCR endpoint blocked by privacy policy.")
    if config.ollama_model.endswith(":cloud") and not config.allow_remote_ocr:
        raise OCRServiceError("Cloud-hosted Ollama models are blocked by privacy policy.")

    payload = {
        "model": config.ollama_model,
        "prompt": OCR_PROMPT,
        "images": [base64_image],
        "stream": False,
        "keep_alive": config.ollama_keep_alive,
    }
    try:
        resp = await _get_client().post(
            f"{config.ollama_base_url}/api/generate",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return _normalize_ocr_response(str(data.get("response", "")))
    except httpx.TimeoutException as exc:
        raise OCRServiceError(
            f"Local OCR timed out after {config.ocr_timeout_seconds} seconds."
        ) from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise OCRServiceError(
                f"Local OCR model '{config.ollama_model}' is not installed. "
                f"Run: ollama pull {config.ollama_model}"
            ) from exc
        raise OCRServiceError(
            f"Local Ollama returned HTTP {exc.response.status_code}."
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise OCRServiceError("Local Ollama request failed.") from exc
