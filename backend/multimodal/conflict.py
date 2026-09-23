import re


# ============================================================
# ORDER ID NORMALIZATION
# ============================================================

def normalize_order_id(order_id):
    """
    Normalize an order ID for comparison.

    Examples:
    ORD12345   -> ORD12345
    ORD-12345  -> ORD12345
    ORDER12345 -> ORD12345
    ORDER-12345 -> ORD12345
    """

    if not order_id:
        return None

    value = (
        str(order_id)
        .replace("-", "")
        .replace(" ", "")
        .upper()
    )

    if value.startswith("ORDER"):
        value = "ORD" + value[5:]

    return value


# ============================================================
# EXTRACT ORDER IDs FROM CUSTOMER MESSAGE
# ============================================================

def extract_message_order_ids(message):
    """
    Extract valid order IDs from the customer's message.

    Valid examples:
    ORD12345
    ORDER12345
    ORD-12345
    ORDER-12345

    The ID must contain digits after ORD/ORDER.
    """

    if not message:
        return []

    pattern = r"\b(?:ORD(?:ER)?[- ]?\d{3,})\b"

    matches = re.findall(
        pattern,
        message,
        re.IGNORECASE
    )

    order_ids = []

    for value in matches:

        normalized = normalize_order_id(value)

        if normalized and normalized not in order_ids:
            order_ids.append(normalized)

    return order_ids


# ============================================================
# COMPARE ORDER IDs
# ============================================================

def compare_order_ids(message, extracted_order_ids):
    """
    Compare order IDs in the customer's message
    with order IDs extracted from the uploaded file.
    """

    message_ids = extract_message_order_ids(
        message
    )

    file_ids = [
        normalize_order_id(order_id)
        for order_id in extracted_order_ids
    ]

    file_ids = [
        value
        for value in file_ids
        if value
    ]

    # --------------------------------------------------------
    # NO INFORMATION TO COMPARE
    # --------------------------------------------------------

    if not message_ids or not file_ids:

        return {
            "status": "NO_COMPARISON",
            "conflict": False,
            "message": (
                "No matching order ID information "
                "was available for comparison."
            )
        }

    # --------------------------------------------------------
    # MATCH
    # --------------------------------------------------------

    matching_ids = (
        set(message_ids) &
        set(file_ids)
    )

    if matching_ids:

        return {
            "status": "MATCH",
            "conflict": False,
            "matching_order_ids":
                sorted(list(matching_ids)),
            "message_order_ids":
                message_ids,
            "file_order_ids":
                file_ids,
            "message": (
                "The order ID in the message "
                "matches the uploaded file."
            )
        }

    # --------------------------------------------------------
    # CONFLICT
    # --------------------------------------------------------

    return {
        "status": "CONFLICT",
        "conflict": True,
        "message_order_ids":
            message_ids,
        "file_order_ids":
            file_ids,
        "message": (
            "The order ID in the customer message "
            "does not match the uploaded file."
        )
    }


# ============================================================
# COMPLETE FILE VS MESSAGE COMPARISON
# ============================================================

def compare_file_with_message(
    message,
    extracted_information
):
    """
    Compare important information from the uploaded
    file with the customer's message.
    """

    order_ids = extracted_information.get(
        "order_ids",
        []
    )

    order_result = compare_order_ids(
        message,
        order_ids
    )

    conflicts = []

    if order_result["conflict"]:

        conflicts.append({
            "field": "order_id",
            "message": order_result["message"]
        })

    if conflicts:

        return {
            "status": "CONFLICT",
            "conflict": True,
            "conflicts": conflicts,
            "message_order_ids":
                order_result.get(
                    "message_order_ids",
                    []
                ),
            "file_order_ids":
                order_result.get(
                    "file_order_ids",
                    []
                )
        }

    return {
        "status":
            order_result["status"],

        "conflict": False,

        "conflicts": [],

        "message_order_ids":
            order_result.get(
                "message_order_ids",
                []
            ),

        "file_order_ids":
            order_result.get(
                "file_order_ids",
                []
            )
    }


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("MULTIMODAL CONFLICT DETECTION TEST")
    print("=" * 60)

    extracted_information = {
        "order_ids": ["ORD12345"]
    }

    # --------------------------------------------------------
    # TEST 1 - MATCH
    # --------------------------------------------------------

    print("\nTest 1 - Matching order ID")
    print("-" * 60)

    result = compare_file_with_message(
        "My order ORD12345 is damaged.",
        extracted_information
    )

    print(result)

    # --------------------------------------------------------
    # TEST 2 - CONFLICT
    # --------------------------------------------------------

    print("\nTest 2 - Conflicting order ID")
    print("-" * 60)

    result = compare_file_with_message(
        "My order ORD99999 is damaged.",
        extracted_information
    )

    print(result)

    # --------------------------------------------------------
    # TEST 3 - NO COMPARISON
    # --------------------------------------------------------

    print("\nTest 3 - No order ID in message")
    print("-" * 60)

    result = compare_file_with_message(
        "The product in the invoice is damaged.",
        extracted_information
    )

    print(result)