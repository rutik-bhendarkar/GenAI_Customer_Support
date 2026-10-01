# ============================================================
# PRODUCTION IMAGE FOR RENDER
# ============================================================
#
# Render's native Python runtime does not include OS-level
# packages, so the Tesseract OCR engine (required for image
# uploads by backend/multimodal/ocr.py) is only available when
# the service runs with the Docker runtime.
#
# Deploy: Render Dashboard -> Service -> Settings -> Build ->
# Source -> Edit -> Runtime: Docker (Dockerfile at repo root).

FROM python:3.12-slim

# System packages
# - tesseract-ocr: OCR engine used by pytesseract for
#   .png/.jpg/.jpeg uploads (PDFs use pure-Python pypdf).
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies in a separate layer so the image cache
# survives source-code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code: backend/, frontend/, data/knowledge_base/
# (runtime upload directories are created at startup).
COPY . .

# Render assigns the listen port through the PORT environment
# variable; fall back to 10000 for local runs.
# uvicorn is started with a single worker to stay inside the
# 512 MB instance memory limit.
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-10000}"]