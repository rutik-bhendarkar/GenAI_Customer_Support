from pathlib import Path

from backend.multimodal.file_handler import (
    create_upload_directories,
    move_to_processed,
    move_to_rejected
)
from backend.multimodal.conflict import (
    compare_file_with_message
)
from backend.multimodal.masking import mask_sensitive_data
from backend.multimodal.ocr import (
    extract_text,
    extract_order_ids,
    extract_dates,
    extract_amounts,
    extract_product_names,
    extract_error_codes
)
from backend.multimodal.retention import cleanup_uploads
from backend.multimodal.validator import (
    validate_file,
    validate_content
)


# ============================================================
# PROCESS MULTIMODAL FILE
# ============================================================

def process_file(file_path,customer_message=None):
    """
    Complete multimodal processing pipeline.

    Steps:
    1. Validate file
    2. Extract text
    3. Validate extracted content
    4. Extract structured information
    5. Move file to processed/rejected
    """

    file_path = Path(file_path)

    create_upload_directories()

    # --------------------------------------------------------
    # STEP 1 - FILE VALIDATION
    # --------------------------------------------------------

    file_validation = validate_file(
        file_path
    )

    if not file_validation["valid"]:

        rejected_path = None

        if file_path.exists():

            rejected_path = move_to_rejected(
                file_path
            )

        return {
            "success": False,
            "stage": "file_validation",
            "filename": file_path.name,
            "message": "File validation failed.",
            "issues":
                file_validation["issues"],
            "processed_file": (
                str(rejected_path)
                if rejected_path
                else None
            )
        }

    # --------------------------------------------------------
    # STEP 2 - TEXT EXTRACTION
    # --------------------------------------------------------

    try:

        extracted_text = extract_text(
            file_path
        )

    except Exception as error:

        rejected_path = move_to_rejected(
            file_path
        )

        return {
            "success": False,
            "stage": "text_extraction",
            "filename": file_path.name,
            "message":
                "Text extraction failed.",
            "error": str(error),
            "processed_file":
                str(rejected_path)
        }

    # --------------------------------------------------------
    # EMPTY DOCUMENT CHECK
    # --------------------------------------------------------

    if not extracted_text.strip():

        rejected_path = move_to_rejected(
            file_path
        )

        return {
            "success": False,
            "stage": "text_extraction",
            "filename": file_path.name,
            "message":
                "No readable text was found in the file.",
            "processed_file":
                str(rejected_path)
        }

    # --------------------------------------------------------
    # STEP 3 - CONTENT SECURITY
    # --------------------------------------------------------

    content_validation = validate_content(
        extracted_text
    )

    if not content_validation["valid"]:

        rejected_path = move_to_rejected(
            file_path
        )

        return {
            "success": False,
            "stage": "content_security",
            "filename": file_path.name,
            "message":
                "File rejected because suspicious "
                "instructions were detected.",
            "detected_patterns":
                content_validation[
                    "detected_patterns"
                ],
            "processed_file":
                str(rejected_path)
        }

    # --------------------------------------------------------
    # STEP 4 - STRUCTURED INFORMATION
    # --------------------------------------------------------

    order_ids = extract_order_ids(
        extracted_text
    )

    dates = extract_dates(
        extracted_text
    )

    amounts = extract_amounts(
        extracted_text
    )

    product_names = extract_product_names(
        extracted_text
    )

    error_codes = extract_error_codes(
        extracted_text
    )

        # --------------------------------------------------------
    # STEP 5 - MESSAGE VS FILE COMPARISON
    # --------------------------------------------------------

    extracted_information = {
        "order_ids": order_ids,
        "dates": dates,
        "amounts": amounts,
        "product_names": product_names,
        "error_codes": error_codes
    }

    comparison_result = {
        "status": "NO_COMPARISON",
        "conflict": False,
        "conflicts": []
    }

    if customer_message:

        comparison_result = (
            compare_file_with_message(
                customer_message,
                extracted_information
            )
        )

        if comparison_result["conflict"]:

            rejected_path = move_to_rejected(
                file_path
            )

            return {
                "success": False,
                "stage": "conflict_detection",
                "filename": file_path.name,
                "message": (
                    "The uploaded file conflicts "
                    "with information provided "
                    "in the customer message. "
                    "Please clarify the information."
                ),
                "comparison":
                    comparison_result,
                "processed_file":
                    str(rejected_path)
            }
    # --------------------------------------------------------
    # STEP 5 - MOVE TO PROCESSED
    # --------------------------------------------------------

    processed_path = move_to_processed(
        file_path
    )

    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    return {
        "success": True,

        "filename":
            file_path.name,

        "message":
            "File processed successfully.",

        "extracted_text":
            mask_sensitive_data(extracted_text),

        "extracted_information": {

            "order_ids":
                order_ids,

            "dates":
                dates,

            "amounts":
                amounts,

            "product_names":
                product_names,

            "error_codes":
                error_codes,

            "comparison":comparison_result
        },

        "processed_file":
            str(processed_path)
    }


# ============================================================
# TEXT-ONLY TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("MULTIMODAL PROCESSOR")
    print("=" * 60)

    print(
        "\nProcessor module loaded successfully."
    )

    print(
        "\nPipeline:"
    )

    print(
        "1. File validation"
    )

    print(
        "2. Text extraction"
    )

    print(
        "3. Content security validation"
    )

    print(
        "4. Structured information extraction"
    )

    print(
        "5. Processed/rejected file handling"
    )

    # ============================================================
# UPLOAD RETENTION CLEANUP
# ============================================================

def cleanup_expired_uploads(retention_hours=24):
    """
    Remove processed and rejected uploads older than
    the configured retention period.
    """

    return cleanup_uploads(
        retention_hours=retention_hours
    )