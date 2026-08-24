$ErrorActionPreference = "Stop"

$backendDir = Join-Path $PSScriptRoot "backend"
$pythonPath = Join-Path $backendDir ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Ambiente Python mancante. Crearlo in Script\backend\.venv e installare requirements.txt."
}

if (-not $env:OCR_ENGINE) { $env:OCR_ENGINE = "rapidocr" }
if (-not $env:OLLAMA_MODEL) { $env:OLLAMA_MODEL = "glm-ocr:q8_0" }
if (-not $env:OLLAMA_BASE_URL) { $env:OLLAMA_BASE_URL = "http://127.0.0.1:11434" }
if (-not $env:ALLOW_REMOTE_OCR) { $env:ALLOW_REMOTE_OCR = "false" }

Set-Location -LiteralPath $backendDir
& $pythonPath -m uvicorn app.main:app --host 127.0.0.1 --port 8000
