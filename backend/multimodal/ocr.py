from pathlib import Path
import os
import re
import shutil

import pytesseract
from PIL import Image
from pypdf import PdfReader


# ============================================================
# TESSERACT OCR ENGINE RESOLUTION
# ============================================================

# Optional environment overrides for the Tesseract executable.
TESSERACT_ENVIRONMENT_VARIABLES = (
    "TESSERACT_CMD",
    "TESSERACT_PATH"
)


# Common Windows installation directories.
WINDOWS_TESSERACT_LOCATIONS = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\ProgramData\chocolatey\bin\tesseract.exe"
)


def resolve_tesseract_command():
    """
    Locate the Tesseract OCR executable.

    Resolution order:

    1. TESSERACT_CMD / TESSERACT_PATH environment variable
    2. tesseract already available on PATH
    3. Common Windows installation directories

    Returns the resolved executable path,
    or None when Tesseract cannot be located.
    """

    # --------------------------------------------------------
    # 1. Environment variable override
    # --------------------------------------------------------

    for variable in TESSERACT_ENVIRONMENT_VARIABLES:

        configured = os.environ.get(variable)

        if configured and Path(configured).is_file():

            return configured

    # --------------------------------------------------------
    # 2. Already available on PATH
    # --------------------------------------------------------

    found_on_path = shutil.which("tesseract")

    if found_on_path:

        return found_on_path

    # --------------------------------------------------------
    # 3. Common per-user / system install locations
    # --------------------------------------------------------

    candidates = list(
        WINDOWS_TESSERACT_LOCATIONS
    )

    local_app_data = os.environ.get(
        "LOCALAPPDATA"
    )

    if local_app_data:

        local_app_data_path = Path(
            local_app_data
        )

        candidates.extend([
            str(
                local_app_data_path
                / "Tesseract-OCR"
                / "tesseract.exe"
            ),
            str(
                local_app_data_path
                / "Programs"
                / "Tesseract-OCR"
                / "tesseract.exe"
            )
        ])

    for candidate in candidates:

        if Path(candidate).is_file():

            return candidate

    return None


# Resolve once at import time so every OCR call
# uses the same executable.
TESSERACT_COMMAND = resolve_tesseract_command()


if TESSERACT_COMMAND:

    pytesseract.pytesseract.tesseract_cmd = (
        TESSERACT_COMMAND
    )


def get_ocr_engine_diagnostics():
    """
    Return non-sensitive diagnostics about the OCR engine
    used for image files.

    Used for logging and for upload error responses so that
    OCR failures can be diagnosed quickly.
    """

    diagnostics = {
        "engine": "tesseract (pytesseract)",
        "executable":
            TESSERACT_COMMAND
            or pytesseract.pytesseract.tesseract_cmd,
        "available": False
    }

    try:

        diagnostics["version"] = str(
            pytesseract.get_tesseract_version()
        )

        diagnostics["available"] = True

    except Exception as error:

        diagnostics["error"] = (
            f"{type(error).__name__}: {error}"
        )

    return diagnostics


# ============================================================
# OCR TEXT EXTRACTION
# ============================================================

def extract_text_from_image(file_path):
    """
    Extract text from an image using Tesseract OCR.
    """
    try:
        image = Image.open(file_path)

        text = pytesseract.image_to_string(image)

        return text.strip()

    except Exception as error:
        raise RuntimeError(
            f"Image OCR failed: {error}"
        ) from error


def extract_text_from_pdf(file_path):
    """
    Extract text from a PDF.

    This handles text-based PDFs.
    Scanned PDFs will be handled in a later step.
    """
    try:
        reader = PdfReader(file_path)

        pages = []

        for page in reader.pages:
            text = page.extract_text()

            if text:
                pages.append(text)

        return "\n".join(pages).strip()

    except Exception as error:
        raise RuntimeError(
            f"PDF text extraction failed: {error}"
        )


def extract_text(file_path):
    """
    Automatically select the appropriate
    extraction method based on file extension.
    """

    file_path = Path(file_path)

    extension = file_path.suffix.lower()

    if extension in {".png", ".jpg", ".jpeg"}:

        return extract_text_from_image(file_path)

    elif extension == ".pdf":

        return extract_text_from_pdf(file_path)

    else:

        raise ValueError(
            f"Unsupported file type: {extension}"
        )


# ============================================================
# INFORMATION EXTRACTION
# ============================================================

def extract_order_ids(text):
    """
    Extract order IDs such as:

    ORD12345
    ORDER12345
    ORD-12345
    ORDER-12345

    The ID must contain digits after ORD/ORDER.
    This prevents values such as ORDDATE from
    being incorrectly detected as an order ID.
    """

    pattern = r"\b(?:ORD(?:ER)?[- ]?\d{3,})\b"

    matches = re.findall(
        pattern,
        text,
        re.IGNORECASE
    )

    order_ids = []

    for match in matches:

        order_id = (
            match
            .replace("-", "")
            .replace(" ", "")
            .upper()
        )

        if order_id.startswith("ORDER"):

            order_id = (
                "ORD" + order_id[5:]
            )

        if order_id not in order_ids:

            order_ids.append(order_id)

    return order_ids


def extract_dates(text):
    """
    Extract common date formats.
    """

    patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{2}/\d{2}/\d{4}\b",
        r"\b\d{2}-\d{2}-\d{4}\b"
    ]

    dates = []

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text
        )

        for value in matches:

            if value not in dates:

                dates.append(value)

    return dates


def extract_amounts(text):
    """
    Extract monetary amounts such as:

    ₹1,299
    Rs. 1299
    Rs 1299
    INR 1299
    $25.50
    USD 25.50
    """

    pattern = (
        r"(?:₹|Rs\.?|INR|\$|USD)"
        r"\s*"
        r"\d+(?:,\d{3})*"
        r"(?:\.\d{1,2})?"
    )

    matches = re.findall(
        pattern,
        text,
        re.IGNORECASE
    )

    return [
        value.strip()
        for value in matches
    ]


def extract_error_codes(text):
    """
    Extract common error-code formats such as:

    ERR-500
    ERROR 404
    E102
    """

    patterns = [
        r"\bERR[- ]?\d{3,5}\b",
        r"\bERROR[- ]?\d{3,5}\b",
        r"\bE\d{3,5}\b"
    ]

    error_codes = []

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            re.IGNORECASE
        )

        for value in matches:

            value = value.upper()

            if value not in error_codes:

                error_codes.append(value)

    return error_codes


def extract_product_names(text):
    """
    Basic product-name extraction.

    Examples:

    Product: Samsung Galaxy Phone
    Item: Laptop
    Model: iPhone 17
    Product Name: Samsung TV
    Item Name: Keyboard
    """

    patterns = [
        r"(?:Product|Item|Model)\s*:\s*([^\n,]+)",
        r"(?:Product Name|Item Name)\s*:\s*([^\n,]+)"
    ]

    products = []

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            re.IGNORECASE
        )

        for value in matches:

            product = value.strip()

            if product and product not in products:

                products.append(product)

    return products


# ============================================================
# COMPLETE EXTRACTION
# ============================================================

def extract_multimodal_information(file_path):
    """
    Extract text and structured information
    from an uploaded file.
    """

    text = extract_text(file_path)

    return {
        "text": text,

        "order_ids":
            extract_order_ids(text),

        "dates":
            extract_dates(text),

        "amounts":
            extract_amounts(text),

        "product_names":
            extract_product_names(text),

        "error_codes":
            extract_error_codes(text)
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("MULTIMODAL OCR MODULE")
    print("=" * 60)

    print(
        "\nOCR module loaded successfully."
    )

    sample_text = """
    Invoice

    Order ID: ORD12345
    Product: Samsung Galaxy Phone
    Order Date: 2026-09-20
    Amount: ₹29,999
    Error Code: ERR-500
    """

    print("\nSample extraction test")
    print("-" * 60)

    print(
        "Order IDs:",
        extract_order_ids(sample_text)
    )

    print(
        "Dates:",
        extract_dates(sample_text)
    )

    print(
        "Amounts:",
        extract_amounts(sample_text)
    )

    print(
        "Products:",
        extract_product_names(sample_text)
    )

    print(
        "Error Codes:",
        extract_error_codes(sample_text)
    )