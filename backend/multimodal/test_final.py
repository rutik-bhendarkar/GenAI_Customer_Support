import shutil
from pathlib import Path

from backend.multimodal.background import (
    process_file_in_background,
    get_processing_status
)


SOURCE_FILE = Path("data/uploads/processed/test_invoice.pdf")
FILE_PATH = Path("data/uploads/incoming/test_invoice.pdf")

CUSTOMER_MESSAGE = (
    "My order ORD12345 is not working."
)


def restore_test_file():
    FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Test fixture not found: {SOURCE_FILE}"
        )

    shutil.copy2(SOURCE_FILE, FILE_PATH)


print("=" * 60)
print("TASK 5 - FINAL MULTIMODAL INTEGRATION TEST")
print("=" * 60)


restore_test_file()


print("\nStarting background processing...")
print("-" * 60)

future = process_file_in_background(
    str(FILE_PATH),
    CUSTOMER_MESSAGE
)


print("\nInitial status:")
print(get_processing_status(future))


print("\nWaiting for processing result...")
print("-" * 60)

result = future.result()


print("\nFinal result:")
print(result)


print("\nFinal status:")
print(get_processing_status(future))


print("\n" + "=" * 60)
print("TASK 5 FINAL TEST COMPLETED")
print("=" * 60)