from backend.multimodal.ocr import (
    extract_order_ids,
    extract_dates,
    extract_amounts,
    extract_product_names,
    extract_error_codes
)

from backend.multimodal.validator import (
    validate_content
)


sample_text = """
INVOICE

Order ID: ORD12345
Product: Samsung Galaxy Phone
Order Date: 2026-09-20
Amount: ₹29,999
Error Code: ERR-500

Customer reports that the product is not working.
"""


print("=" * 60)
print("TASK 5 - MULTIMODAL EXTRACTION TEST")
print("=" * 60)


print("\nExtracted Order IDs:")
print(
    extract_order_ids(sample_text)
)


print("\nExtracted Dates:")
print(
    extract_dates(sample_text)
)


print("\nExtracted Amounts:")
print(
    extract_amounts(sample_text)
)


print("\nExtracted Products:")
print(
    extract_product_names(sample_text)
)


print("\nExtracted Error Codes:")
print(
    extract_error_codes(sample_text)
)


print("\nSecurity Validation:")
print(
    validate_content(sample_text)
)


print("\n" + "=" * 60)
print("TEST COMPLETED")
print("=" * 60)