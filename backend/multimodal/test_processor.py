from backend.multimodal.processor import process_file


file_path = "data/uploads/incoming/test_invoice.pdf"


print("=" * 60)
print("TASK 5 - COMPLETE PDF PROCESSING TEST")
print("=" * 60)

result = process_file(file_path)

print("\nProcessing Result:")
print("-" * 60)

print(f"Success: {result['success']}")
print(f"Filename: {result['filename']}")
print(f"Message: {result['message']}")

if result["success"]:

    print("\nExtracted Information:")
    print("-" * 60)

    information = result[
        "extracted_information"
    ]

    print(
        "Order IDs:",
        information["order_ids"]
    )

    print(
        "Dates:",
        information["dates"]
    )

    print(
        "Amounts:",
        information["amounts"]
    )

    print(
        "Products:",
        information["product_names"]
    )

    print(
        "Error Codes:",
        information["error_codes"]
    )

    print(
        "\nProcessed File:",
        result["processed_file"]
    )

else:

    print("\nError Stage:")
    print(
        result.get("stage")
    )

    print(
        "Issues:",
        result.get("issues")
    )

print("\n" + "=" * 60)