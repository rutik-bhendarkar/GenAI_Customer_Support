import re


# ============================================================
# EXTRACT TICKET INFORMATION
# ============================================================

def extract_ticket_information(message: str):
    """
    Extract basic support-ticket information
    from a customer message.
    """

    text = message.strip()

    # ========================================================
    # 1. EXTRACT ORDER ID
    # ========================================================

    order_id = None

    # Supported formats:
    #
    # ORD12345
    # ORD-12345
    # ORD 12345
    # ORDER12345
    # ORDER-12345
    # ORDER 12345
    #
    # At least 3 digits are required.
    #
    # This prevents:
    #
    # "order issue"   -> ORDISSUE ❌
    # "order problem" -> ORDPROBLEM ❌
    #
    # from being treated as order IDs.

    order_match = re.search(
        r"\b(?:ORDER|ORD)[- ]?(\d{3,})\b",
        text,
        re.IGNORECASE
    )

    if order_match:

        digits = order_match.group(1)

        order_id = f"ORD{digits}"

    # ========================================================
    # 2. EXTRACT CUSTOMER NAME
    # ========================================================

    customer = None

    name_patterns = [
        r"\bmy name is ([A-Za-z]+(?:\s[A-Za-z]+)?)",
        r"\bI am ([A-Za-z]+(?:\s[A-Za-z]+)?)",
        r"\bI'm ([A-Za-z]+(?:\s[A-Za-z]+)?)"
    ]

    for pattern in name_patterns:

        name_match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if name_match:

            customer = name_match.group(1).strip()

            break

    # ========================================================
    # 3. EXTRACT CONTACT DETAILS
    # ========================================================

    email_match = re.search(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        text
    )

    phone_match = re.search(
        r"\b(?:\+91[- ]?)?[6-9]\d{9}\b",
        text
    )

    contact_details = None

    if email_match:

        contact_details = email_match.group(0)

    elif phone_match:

        contact_details = phone_match.group(0)

    # ========================================================
    # 4. DETECT PRODUCT
    # ========================================================

    product = None

    product_keywords = [
        "laptop",
        "phone",
        "mobile",
        "smartphone",
        "tablet",
        "headphones",
        "earphones",
        "watch",
        "monitor",
        "keyboard",
        "mouse",
        "charger",
        "television",
        "tv"
    ]

    lower_text = text.lower()

    for item in product_keywords:

        if item in lower_text:

            product = item

            break

    # ========================================================
    # 5. DETECT ISSUE
    # ========================================================

    issue = text

    issue_keywords = {

        "not delivered":
            "Order has not been delivered",

        "not arrived":
            "Order has not arrived",

        "hasn't arrived":
            "Order has not arrived",

        "late":
            "Order delivery is delayed",

        "delayed":
            "Order delivery is delayed",

        "damaged":
            "Product was damaged",

        "broken":
            "Product is broken",

        "refund":
            "Customer is requesting a refund",

        "payment":
            "Customer has a payment-related issue",

        "charged twice":
            "Customer was charged twice",

        "duplicate payment":
            "Customer reports duplicate payment",

        "hacked":
            "Customer reports account compromise",

        "login":
            "Customer has a login issue",

        "password":
            "Customer has a password issue"
    }

    for keyword, description in issue_keywords.items():

        if keyword in lower_text:

            issue = description

            break

    # ========================================================
    # RETURN EXTRACTED INFORMATION
    # ========================================================

    return {
        "customer": customer,
        "order_id": order_id,
        "product": product,
        "issue": issue,
        "contact_details": contact_details
    }


# ============================================================
# CHECK MISSING INFORMATION
# ============================================================

def check_missing_information(ticket_info: dict):
    """
    Check whether mandatory information is missing
    before creating a support ticket.
    """

    missing_fields = []

    # Order ID is mandatory for order-related tickets.
    if ticket_info["order_id"] is None:

        missing_fields.append("order_id")

    return missing_fields


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":

    test_messages = [

        # Standard ORD format
        "My order ORD12345 for my laptop has not arrived yet.",

        # ORD with hyphen
        "My order ORD-12345 is delayed.",

        # ORD with space
        "My order ORD 12345 is delayed.",

        # ORDER format
        "My order ORDER56789 is not working.",

        # ORDER with hyphen
        "My order ORDER-56789 is not working.",

        # ORDER with space
        "My order ORDER 56789 is not working.",

        # Customer + email + order
        "I am Amit. Please contact me at amit@gmail.com. "
        "My mobile order ORD99999 is delayed.",

        # No order ID
        "My laptop hasn't arrived.",

        # IMPORTANT: these must NOT become order IDs
        "Please continue with my order issue.",

        "My order has a problem.",

        "I have an order problem.",

        # Multiple words after order - should NOT become ID
        "My order issue is not resolved."
    ]

    print("=" * 60)
    print("ORDER ID EXTRACTION TEST")
    print("=" * 60)

    for message in test_messages:

        print("\n--------------------------------")
        print("Customer Message:")
        print(message)

        ticket_info = extract_ticket_information(
            message
        )

        print("\nExtracted Information:")
        print(ticket_info)

        missing = check_missing_information(
            ticket_info
        )

        print("\nMissing Mandatory Information:")

        if missing:

            print(missing)

            print(
                "\nPlease provide your order ID "
                "so I can create a support ticket."
            )

        else:

            print("None - Ticket can be created.")