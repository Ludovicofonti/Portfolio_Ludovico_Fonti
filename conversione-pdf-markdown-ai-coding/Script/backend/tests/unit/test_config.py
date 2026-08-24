from app.config import AppConfig, is_loopback_url


def test_loopback_detection_is_strict():
    assert is_loopback_url("http://localhost:11434")
    assert is_loopback_url("http://127.0.0.1:11434")
    assert is_loopback_url("http://[::1]:11434")
    assert not is_loopback_url("https://ollama.example.com")
    assert not is_loopback_url("http://localhost.example.com:11434")


def test_remote_ocr_is_blocked_by_default(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "https://ocr.example.com")
    monkeypatch.delenv("ALLOW_REMOTE_OCR", raising=False)
    candidate = AppConfig()
    assert not candidate.ocr_endpoint_is_private
    assert not candidate.remote_ocr_allowed


def test_cpu_friendly_defaults(monkeypatch):
    for name in (
        "OLLAMA_MODEL",
        "RENDER_DPI",
        "MAX_PAGE_COUNT",
        "MAX_CONCURRENT_JOBS",
    ):
        monkeypatch.delenv(name, raising=False)
    candidate = AppConfig()
    assert candidate.ollama_model == "glm-ocr:q8_0"
    assert candidate.ocr_engine == "rapidocr"
    assert candidate.render_dpi == 72
    assert candidate.max_page_count == 50
    assert candidate.max_concurrent_jobs == 1
