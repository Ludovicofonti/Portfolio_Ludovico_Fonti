import os
import ipaddress
from urllib.parse import urlparse


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def is_loopback_url(url: str) -> bool:
    """Return True only for HTTP(S) endpoints bound to this computer."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    if parsed.hostname.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(parsed.hostname).is_loopback
    except ValueError:
        return False


class AppConfig:
    def __init__(self) -> None:
        self.ocr_engine: str = os.getenv("OCR_ENGINE", "rapidocr").strip().lower()
        self.ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model: str = os.getenv("OLLAMA_MODEL", "glm-ocr:q8_0")
        self.allow_remote_ocr: bool = _env_bool("ALLOW_REMOTE_OCR", False)
        max_size_mb = int(os.getenv("MAX_FILE_SIZE_MB", "25"))
        self.max_file_size_bytes: int = max_size_mb * 1024 * 1024
        self.max_batch_files: int = int(os.getenv("MAX_BATCH_FILES", "5"))
        max_batch_mb = int(os.getenv("MAX_BATCH_SIZE_MB", "100"))
        self.max_batch_size_bytes: int = max_batch_mb * 1024 * 1024
        self.ocr_timeout_seconds: int = int(os.getenv("OCR_TIMEOUT_SECONDS", "300"))
        self.ollama_keep_alive: str = os.getenv("OLLAMA_KEEP_ALIVE", "10m")
        # 72 DPI keeps OCR practical on low-end CPU-only machines; raise it only
        # for unusually small or degraded scans.
        self.render_dpi: int = int(os.getenv("RENDER_DPI", "72"))
        self.native_text_min_chars: int = int(os.getenv("NATIVE_TEXT_MIN_CHARS", "20"))
        self.max_page_count: int = int(os.getenv("MAX_PAGE_COUNT", "50"))
        self.max_concurrent_jobs: int = int(os.getenv("MAX_CONCURRENT_JOBS", "1"))
        self.job_ttl_seconds: int = int(os.getenv("JOB_TTL_SECONDS", "3600"))

    @property
    def ocr_endpoint_is_private(self) -> bool:
        return is_loopback_url(self.ollama_base_url)

    @property
    def remote_ocr_allowed(self) -> bool:
        return self.allow_remote_ocr or self.ocr_endpoint_is_private


config = AppConfig()
