"""
Shared pytest configuration for the automated test suite.

The multimodal tests use a small invoice PDF as their fixture. The
fixture lives in `data/uploads/processed/test_invoice.pdf`, which is a
runtime directory and is therefore not committed to git. To keep the
suite self-sufficient on a fresh clone, this module regenerates the
exact same document when it is missing.

The generator only runs when the file does not exist, so a manually
created fixture is never overwritten.
"""

from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent

INVOICE_FIXTURE = (
    PROJECT_ROOT
    / "data"
    / "uploads"
    / "processed"
    / "test_invoice.pdf"
)


# Content of the fixture document. Keep in sync with the expectations
# in tests/test_support_conditions.py and tests/test_upload_endpoint.py.
INVOICE_LINES = [
    "INVOICE",
    "Order ID: ORD12345",
    "Product: Samsung Galaxy Phone",
    "Order Date: 2026-09-20",
    "Amount: Rs. 29,999",
    "Error Code: ERR-500",
    "Customer reports that the product is not working.",
]


def build_invoice_fixture(path):
    """
    Create the text-based invoice PDF used by the multimodal tests.

    Returns True when the file was created.
    """

    from reportlab.pdfgen import canvas

    path.parent.mkdir(parents=True, exist_ok=True)

    pdf = canvas.Canvas(str(path))

    y_position = 780

    for line in INVOICE_LINES:

        pdf.drawString(72, y_position, line)

        y_position -= 20

    pdf.showPage()
    pdf.save()

    return path.exists()


@pytest.fixture(scope="session", autouse=True)
def ensure_invoice_fixture():
    """
    Ensure the PDF invoice fixture exists before the tests run.

    Failure to create the fixture is not fatal: the tests that need it
    skip themselves with a clear reason.
    """

    return ensure_invoice_fixture_file()


def ensure_invoice_fixture_file():
    """
    Create the invoice PDF fixture when it is missing.

    Returns the fixture path, or None when it could not be created.
    """

    if INVOICE_FIXTURE.exists():

        return INVOICE_FIXTURE

    try:

        build_invoice_fixture(INVOICE_FIXTURE)

    except Exception as error:  # pragma: no cover - environment issue

        print(
            "\n[conftest] Could not create the invoice fixture "
            f"({type(error).__name__}: {error}). "
            "PDF fixture tests will be skipped."
        )

        return None

    return INVOICE_FIXTURE


def pytest_configure(config):
    """
    Create the fixture before the test modules are imported.

    The PDF tests use `pytest.mark.skipif` with an existence check, and
    skip conditions are evaluated while the module is imported. Running
    the generator here - before collection - keeps those tests
    independent of any manual setup, so they also run on a fresh clone
    instead of being skipped once.
    """

    ensure_invoice_fixture_file()

