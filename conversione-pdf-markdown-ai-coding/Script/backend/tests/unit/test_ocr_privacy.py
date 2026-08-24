import httpx
import pytest

from app.config import config
from app.services import ocr_client


@pytest.mark.asyncio
async def test_remote_endpoint_is_rejected_without_network(monkeypatch):
    await ocr_client.close_ocr_client()
    monkeypatch.setattr(config, "ollama_base_url", "https://ocr.example.com")
    monkeypatch.setattr(config, "allow_remote_ocr", False)

    status = await ocr_client.get_ollama_status()

    assert not status.ready
    assert not status.privacy_ok
    assert "blocked" in status.error_message.lower()


@pytest.mark.asyncio
async def test_cloud_model_is_rejected_even_through_local_ollama(monkeypatch):
    await ocr_client.close_ocr_client()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "models": [
                    {
                        "name": "glm-ocr:cloud",
                        "remote_host": "https://ollama.com:443",
                    }
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(config, "ollama_base_url", "http://127.0.0.1:11434")
    monkeypatch.setattr(config, "ollama_model", "glm-ocr:cloud")
    monkeypatch.setattr(config, "allow_remote_ocr", False)
    monkeypatch.setattr(ocr_client, "_client", client)
    try:
        status = await ocr_client.get_ollama_status()
        assert not status.ready
        assert not status.model_local
        assert not status.privacy_ok
    finally:
        await ocr_client.close_ocr_client()


@pytest.mark.asyncio
async def test_local_model_is_accepted(monkeypatch):
    await ocr_client.close_ocr_client()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"models": [{"name": "glm-ocr:q8_0", "size": 1_600_000_000}]},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(config, "ollama_base_url", "http://127.0.0.1:11434")
    monkeypatch.setattr(config, "ollama_model", "glm-ocr:q8_0")
    monkeypatch.setattr(config, "allow_remote_ocr", False)
    monkeypatch.setattr(ocr_client, "_client", client)
    try:
        status = await ocr_client.get_ollama_status()
        assert status.ready
        assert status.model_local
        assert status.privacy_ok
    finally:
        await ocr_client.close_ocr_client()


@pytest.mark.asyncio
async def test_ocr_uses_image_marker_and_unwraps_markdown(monkeypatch):
    await ocr_client.close_ocr_client()

    def handler(request: httpx.Request) -> httpx.Response:
        payload = __import__("json").loads(request.content)
        assert "[img-0]" in payload["prompt"]
        assert payload["images"] == ["synthetic-image"]
        return httpx.Response(200, json={"response": "```markdown\n# Private local OCR\n```"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(config, "ollama_base_url", "http://127.0.0.1:11434")
    monkeypatch.setattr(config, "ollama_model", "glm-ocr:q8_0")
    monkeypatch.setattr(config, "allow_remote_ocr", False)
    monkeypatch.setattr(ocr_client, "_client", client)
    try:
        assert await ocr_client.ocr_page("synthetic-image") == "# Private local OCR"
    finally:
        await ocr_client.close_ocr_client()


@pytest.mark.asyncio
async def test_ocr_rejects_empty_fenced_markdown(monkeypatch):
    await ocr_client.close_ocr_client()

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"response": "```markdown\n\n```"})
        )
    )
    monkeypatch.setattr(config, "ollama_base_url", "http://127.0.0.1:11434")
    monkeypatch.setattr(config, "allow_remote_ocr", False)
    monkeypatch.setattr(ocr_client, "_client", client)
    try:
        with pytest.raises(ocr_client.OCRServiceError, match="no usable text"):
            await ocr_client.ocr_page("synthetic-image")
    finally:
        await ocr_client.close_ocr_client()
