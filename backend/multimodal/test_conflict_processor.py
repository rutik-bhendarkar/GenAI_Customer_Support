import shutil
from pathlib import Path

from backend.multimodal.processor import process_file


SOURCE_FILE = Path("data/uploads/processed/test_invoice.pdf")
FILE_PATH = Path("data/uploads/incoming/test_invoice.pdf")


def restore_test_file():
    FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Test fixture not found: {SOURCE_FILE}"
        )

    shutil.copy2(SOURCE_FILE, FILE_PATH)


print("=" * 60)
print("TASK 5 - PROCESSOR CONFLICT TEST")
print("=" * 60)


# ============================================================
# TEST 1 - MATCH
# ============================================================

restore_test_file()

print("\nTest 1 - Matching order ID")
print("-" * 60)

result = process_file(
    str(FILE_PATH),
    customer_message="My order ORD12345 is not working."
)

print(result)

print("\nTest 1 completed.")