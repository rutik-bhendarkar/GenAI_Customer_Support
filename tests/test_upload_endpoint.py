"""
End-to-end tests for the multimodal upload endpoint (POST /upload).

These tests reuse the existing FastAPI application and the existing
multimodal pipeline. Image fixtures are generated on the fly so the
tests do not depend on committed screenshots.
"""

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

from backend.main import app
from backend.multimodal.ocr import (
    get_ocr_engine_diagnostics
)


client = TestClient(app)


INVOICE_PDF = Path("data/uploads/processed/test_invoice.pdf")


def ocr_available():
    """
    Tesseract OCR is an external dependency, so image tests are
    skipped (not failed) on machines without it installed.
    """

    return get_ocr_engine_diagnostics()["available"]


requires_ocr = pytest.mark.skipif(
    not ocr_available(),
    reason="Tesseract OCR engine is not available."
)


def build_image(text, image_format="PNG"):
    """
    Build a simple readable image containing the given text.
    """

    image = Image.new(
        "RGB",
        (1000, 300),
        "white"
    )

    draw = ImageDraw.Draw(image)

    font = ImageFont.load_default(size=48)

    draw.text(
        (30, 120),
        text,
        fill="black",
        font=font
    )

    buffer = io.BytesIO()

    image.save(
        buffer,
        format=image_format
    )

    buffer.seek(0)

    return buffer


def build_blank_image(image_format="PNG"):
    """
    Build an image without any readable text.
    """

    image = Image.new(
        "RGB",
        (600, 300),
        "white"
    )

    buffer = io.BytesIO()

    image.save(
        buffer,
        format=image_format
    )

    buffer.seek(0)

    return buffer


def upload_file(
    filename,
    buffer,
    content_type,
    customer_message=""
):
    return client.post(
        "/upload",
        files={
            "file": (
                filename,
                buffer,
                content_type
            )
        },
        data={
            "customer_message": customer_message
        }
    )


# ============================================================
# HEALTH CHECK
# ============================================================

def test_home_endpoint():

    response = client.get("/")

    assert response.status_code == 200

    assert response.json()["status"] == "online"


# ============================================================
# PDF UPLOAD
# ============================================================

@pytest.mark.skipif(
    not INVOICE_PDF.exists(),
    reason="PDF fixture data/uploads/processed/test_invoice.pdf is missing."
)
def test_pdf_upload_matching_message():

    with INVOICE_PDF.open("rb") as pdf_file:

        response = upload_file(
            "test_invoice.pdf",
            pdf_file,
            "application/pdf",
            "My order ORD12345 has not been delivered."
        )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True

    information = data["extracted_information"]

    assert "ORD12345" in information["order_ids"]

    assert information["comparison"]["status"] == "MATCH"

    assert information["comparison"]["conflict"] is False


# ============================================================
# IMAGE UPLOAD (OCR)
# ============================================================

@requires_ocr
def test_png_upload_extracts_text_and_information():

    response = upload_file(
        "test_order.png",
        build_image("Order ID: ORD12345"),
        "image/png"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True

    assert data["extracted_text"].strip()

    information = data["extracted_information"]

    assert information["order_ids"] == ["ORD12345"]

    assert information["comparison"]["status"] == "NO_COMPARISON"

    assert information["comparison"]["conflict"] is False

    assert data["processed_file"]


@requires_ocr
def test_jpg_upload_extracts_information():

    response = upload_file(
        "test_order.jpg",
        build_image("Order ID: ORD12345", image_format="JPEG"),
        "image/jpeg"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True

    assert "ORD12345" in data["extracted_information"]["order_ids"]


@requires_ocr
def test_image_upload_matching_message():

    response = upload_file(
        "test_match.png",
        build_image("Order ID: ORD12345"),
        "image/png",
        "My order ORD12345 has not been delivered."
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True

    comparison = data["extracted_information"]["comparison"]

    assert comparison["status"] == "MATCH"

    assert comparison["conflict"] is False

    assert comparison["message_order_ids"] == ["ORD12345"]

    assert comparison["file_order_ids"] == ["ORD12345"]


@requires_ocr
def test_image_upload_conflicting_message():

    response = upload_file(
        "test_conflict.png",
        build_image("Order ID: ORD99999"),
        "image/png",
        "My order ORD12345 has not been delivered."
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is False

    assert data["stage"] == "conflict_detection"

    assert data["comparison"]["conflict"] is True


@requires_ocr
def test_image_without_text_is_rejected_cleanly():

    response = upload_file(
        "test_blank.png",
        build_blank_image(),
        "image/png"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is False

    assert data["stage"] == "text_extraction"

    assert data["error"]

    assert data["ocr_engine"]["available"] is True


# ============================================================
# UNSUPPORTED FILE TYPE
# ============================================================

def test_unsupported_file_type_is_rejected():

    response = upload_file(
        "document.exe",
        io.BytesIO(b"not a real document"),
        "application/octet-stream"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is False

    assert data["stage"] == "file_validation"

    assert data["message"] == "Unsupported file type."

