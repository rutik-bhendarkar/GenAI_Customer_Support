"""
Deployment configuration regression tests.

Render's native Python runtime has no OS-level packages, so the
production image (Dockerfile) must install the Tesseract OCR
engine that image uploads depend on. These tests keep the Docker
runtime configuration in the repository from regressing.
"""

from pathlib import Path

from backend.multimodal.ocr import get_ocr_engine_diagnostics


ROOT = Path(__file__).resolve().parent.parent

DOCKERFILE = ROOT / "Dockerfile"
DOCKERIGNORE = ROOT / ".dockerignore"


def test_dockerfile_exists():
    """
    The repository must ship a Dockerfile so Render can run the
    service with the Docker runtime (which includes Tesseract).
    """

    assert DOCKERFILE.is_file()


def test_dockerfile_installs_tesseract_ocr():
    """
    The production image must contain the system Tesseract
    executable used by pytesseract for image uploads.
    """

    content = DOCKERFILE.read_text(encoding="utf-8")

    assert "apt-get" in content
    assert "tesseract-ocr" in content


def test_dockerfile_runs_the_api_on_the_render_port():
    """
    The container must honour Render's PORT environment variable
    and start the FastAPI application.
    """

    content = DOCKERFILE.read_text(encoding="utf-8")

    assert "uvicorn backend.main:app" in content
    assert "--host 0.0.0.0" in content
    assert "${PORT" in content


def test_dockerfile_uses_the_project_python_version():
    """
    The image must match the Python version pinned in
    .python-version.
    """

    python_version = (
        ROOT / ".python-version"
    ).read_text(encoding="utf-8").strip()

    content = DOCKERFILE.read_text(encoding="utf-8")

    assert f"python:{python_version}" in content


def test_dockerignore_excludes_secrets_and_runtime_state():
    """
    Secrets and local runtime state must never enter the image
    build context.
    """

    content = DOCKERIGNORE.read_text(encoding="utf-8")

    lines = {
        line.strip()
        for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    }

    assert ".env" in lines
    assert ".venv" in lines
    assert "data/uploads" in lines


def test_ocr_engine_diagnostics_report_availability():
    """
    OCR failures must stay diagnosable: the diagnostics block
    always reports whether the Tesseract executable is usable.
    """

    diagnostics = get_ocr_engine_diagnostics()

    assert diagnostics["engine"] == "tesseract (pytesseract)"
    assert diagnostics["available"] in {True, False}

    if not diagnostics["available"]:
        assert "error" in diagnostics