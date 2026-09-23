import re
import shutil
from pathlib import Path


# ==========================================
# REQUIRED METADATA
# ==========================================

REQUIRED_METADATA = [
    "Document",
    "Version",
    "Product",
    "Region",
    "Effective Date",
    "Expiry Date",
    "Access Level"
]


# ==========================================
# READ DOCUMENT
# ==========================================

def read_document(file_path: Path) -> str:
    """
    Read the content of a knowledge-base document.
    """

    try:
        return file_path.read_text(
            encoding="utf-8"
        )

    except Exception as error:
        raise ValueError(
            f"Unable to read document: {error}"
        )


# ==========================================
# EXTRACT METADATA
# ==========================================

def extract_metadata(content: str) -> dict:
    """
    Extract required metadata from a document.
    """

    metadata = {}

    for field in REQUIRED_METADATA:

        pattern = rf"^{re.escape(field)}:\s*(.+)$"

        match = re.search(
            pattern,
            content,
            re.MULTILINE | re.IGNORECASE
        )

        if match:
            metadata[field] = match.group(1).strip()

    return metadata


# ==========================================
# VALIDATE DOCUMENT
# ==========================================

def validate_document(file_path: Path) -> dict:
    """
    Validate required document metadata.
    """

    content = read_document(file_path)

    metadata = extract_metadata(content)

    missing_fields = [
        field
        for field in REQUIRED_METADATA
        if field not in metadata
    ]

    if missing_fields:

        return {
            "filename": file_path.name,
            "valid": False,
            "missing_fields": missing_fields,
            "metadata": metadata,
            "reason": "Required metadata is missing"
        }

    return {
        "filename": file_path.name,
        "valid": True,
        "missing_fields": [],
        "metadata": metadata,
        "reason": "Document validation successful"
    }


# ==========================================
# QUARANTINE INVALID DOCUMENT
# ==========================================

def quarantine_document(file_path: Path) -> dict:
    """
    Move an invalid document to quarantine.
    """

    quarantine_folder = Path(
        "data/knowledge_base/quarantine"
    )

    quarantine_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    destination = (
        quarantine_folder / file_path.name
    )

    shutil.move(
        str(file_path),
        str(destination)
    )

    return {
        "filename": file_path.name,
        "status": "QUARANTINED",
        "path": str(destination)
    }


# ==========================================
# QUALITY CHECK
# ==========================================

def quality_check(file_path: Path) -> dict:
    """
    Perform quality and security checks
    before document activation.
    """

    try:

        content = read_document(file_path)

    except Exception as error:

        return {
            "filename": file_path.name,
            "passed": False,
            "checks": {
                "readable": False
            },
            "issues": [str(error)]
        }

    validation = validate_document(
        file_path
    )

    issues = []

    checks = {
        "readable": True,
        "metadata_valid": validation["valid"],
        "content_present": bool(
            content.strip()
        ),
        "minimum_content_length": (
            len(content.strip()) >= 100
        ),
        "prompt_injection_check": True
    }

    # --------------------------------------
    # Metadata check
    # --------------------------------------

    if not validation["valid"]:

        issues.append(
            "Required metadata is missing"
        )

    # --------------------------------------
    # Content check
    # --------------------------------------

    if not content.strip():

        issues.append(
            "Document is empty"
        )

    elif len(content.strip()) < 100:

        issues.append(
            "Document content is too short"
        )

    # --------------------------------------
    # Prompt injection check
    # --------------------------------------

    suspicious_patterns = [
        "ignore previous instructions",
        "ignore all previous instructions",
        "disregard previous instructions",
        "system prompt",
        "reveal your instructions",
        "bypass security"
    ]

    content_lower = content.lower()

    for pattern in suspicious_patterns:

        if pattern in content_lower:

            checks[
                "prompt_injection_check"
            ] = False

            issues.append(
                f"Suspicious instruction detected: {pattern}"
            )

            break

    passed = all(checks.values())

    return {
        "filename": file_path.name,
        "passed": passed,
        "checks": checks,
        "issues": issues
    }


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    incoming_folder = Path(
        "data/knowledge_base/incoming"
    )

    print("\nDocument Validation")
    print("===================")

    if not incoming_folder.exists():

        print("Incoming folder does not exist.")

    else:

        # ----------------------------------
        # VALIDATION TEST
        # ----------------------------------

        for file_path in list(
            incoming_folder.iterdir()
        ):

            if not file_path.is_file():
                continue

            result = validate_document(
                file_path
            )

            print(
                "\nFilename:",
                result["filename"]
            )

            print(
                "Valid:",
                result["valid"]
            )

            if result["valid"]:

                print("Status: VALID")

            else:

                print("Status: INVALID")

                print(
                    "Missing:",
                    ", ".join(
                        result["missing_fields"]
                    )
                )

            print(
                "Reason:",
                result["reason"]
            )

        # ----------------------------------
        # QUALITY TEST
        # ----------------------------------

        print("\nQuality Testing")
        print("===============")

        for file_path in list(
            incoming_folder.iterdir()
        ):

            if not file_path.is_file():
                continue

            quality_result = quality_check(
                file_path
            )

            print(
                "\nFilename:",
                quality_result["filename"]
            )

            print(
                "Quality Passed:",
                quality_result["passed"]
            )

            print(
                "Checks:",
                quality_result["checks"]
            )

            if quality_result["issues"]:

                print("Issues:")

                for issue in quality_result["issues"]:

                    print("-", issue)

            else:

                print("Issues: None")