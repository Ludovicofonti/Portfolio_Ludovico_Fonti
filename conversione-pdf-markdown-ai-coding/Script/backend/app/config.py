import os


class AppConfig:
    def __init__(self) -> None:
        self.ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model: str = os.getenv("OLLAMA_MODEL", "glm-ocr")
        max_size_mb = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
        self.max_file_size_bytes: int = max_size_mb * 1024 * 1024
        self.ocr_timeout_seconds: int = int(os.getenv("OCR_TIMEOUT_SECONDS", "600"))
        self.render_dpi: int = int(os.getenv("RENDER_DPI", "150"))
        self.max_page_count: int = int(os.getenv("MAX_PAGE_COUNT", "200"))
        self.job_ttl_seconds: int = int(os.getenv("JOB_TTL_SECONDS", "3600"))


config = AppConfig()
