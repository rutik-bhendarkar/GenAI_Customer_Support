from typing import List, Dict


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text: str) -> str:
    """
    Normalize text for comparison.
    """

    return " ".join(
        text.lower()
        .strip()
        .split()
    )


# ============================================================
# CALCULATE ISSUE SIMILARITY
# ============================================================

def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calculate simple word-based similarity
    using Jaccard similarity.
    """

    words1 = set(
        normalize_text(text1).split()
    )

    words2 = set(
        normalize_text(text2).split()
    )

    if not words1 or not words2:
        return 0.0

    intersection = words1.intersection(words2)

    union = words1.union(words2)

    return len(intersection) / len(union)


# ============================================================
# FIND DUPLICATE TICKET
# ============================================================

def find_duplicate_ticket(
    new_ticket: Dict,
    existing_tickets: List[Dict],
    similarity_threshold: float = 0.5
):
    """
    Check whether the new ticket is a duplicate
    of an existing ticket.

    Duplicate conditions:

    1. Same order + similar issue
       when customer information is unavailable.

    2. Same customer + same order + similar issue
       when customer information is available.
    """

    new_order_id = new_ticket.get("order_id")

    new_customer = new_ticket.get("customer")

    new_issue = new_ticket.get("issue", "")

    # ========================================================
    # CHECK AGAINST EXISTING TICKETS
    # ========================================================

    for ticket in existing_tickets:

        existing_order_id = ticket.get("order_id")

        existing_customer = ticket.get("customer")

        existing_issue = ticket.get("issue", "")

        # ====================================================
        # SAME ORDER
        # ====================================================

        same_order = (
            new_order_id is not None
            and existing_order_id is not None
            and new_order_id == existing_order_id
        )

        # ====================================================
        # SAME CUSTOMER
        # ====================================================

        same_customer = (
            new_customer is not None
            and existing_customer is not None
            and normalize_text(new_customer)
            == normalize_text(existing_customer)
        )

        # ====================================================
        # ISSUE SIMILARITY
        # ====================================================

        similarity = calculate_similarity(
            new_issue,
            existing_issue
        )

        # ====================================================
        # DUPLICATE DETECTION
        # ====================================================

        if same_order and similarity >= similarity_threshold:

            # ------------------------------------------------
            # CASE 1:
            # Both customer names are available
            # ------------------------------------------------

            if (
                new_customer is not None
                and existing_customer is not None
            ):

                if same_customer:

                    return {
                        "is_duplicate": True,
                        "existing_ticket_id":
                            ticket.get("ticket_id"),
                        "similarity":
                            round(similarity, 2),
                        "reason":
                            "Same customer, order and similar issue."
                    }

            # ------------------------------------------------
            # CASE 2:
            # Customer information is unavailable
            # ------------------------------------------------

            else:

                return {
                    "is_duplicate": True,
                    "existing_ticket_id":
                        ticket.get("ticket_id"),
                    "similarity":
                        round(similarity, 2),
                    "reason":
                        "Same order and similar issue; "
                        "customer information unavailable."
                }

    # ========================================================
    # NO DUPLICATE FOUND
    # ========================================================

    return {
        "is_duplicate": False,
        "existing_ticket_id": None,
        "similarity": 0.0,
        "reason": "No duplicate ticket found."
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("\n========================================")
    print("DUPLICATE DETECTION TESTS")
    print("========================================")

    # ========================================================
    # TEST 1
    # Same customer + same order + similar issue
    # ========================================================

    print("\nTest 1 - Same customer and order")

    existing = [
        {
            "ticket_id": "TKT-0001",
            "customer": "Rahul",
            "order_id": "ORD12345",
            "issue": "Order has not arrived"
        }
    ]

    new_ticket = {
        "customer": "Rahul",
        "order_id": "ORD12345",
        "issue": "Order has still not arrived"
    }

    result = find_duplicate_ticket(
        new_ticket,
        existing
    )

    print(result)

    # ========================================================
    # TEST 2
    # Same order + similar issue
    # Customer unavailable
    # ========================================================

    print("\nTest 2 - Same order, customer unavailable")

    existing = [
        {
            "ticket_id": "TKT-0002",
            "customer": None,
            "order_id": "ORD99999",
            "issue": "My order ORD99999 has not been delivered yet"
        }
    ]

    new_ticket = {
        "customer": None,
        "order_id": "ORD99999",
        "issue": "My order ORD99999 has not been delivered yet"
    }

    result = find_duplicate_ticket(
        new_ticket,
        existing
    )

    print(result)

    # ========================================================
    # TEST 3
    # Different order
    # Should NOT be duplicate
    # ========================================================

    print("\nTest 3 - Different order")

    existing = [
        {
            "ticket_id": "TKT-0003",
            "customer": "Rahul",
            "order_id": "ORD12345",
            "issue": "Order has not arrived"
        }
    ]

    new_ticket = {
        "customer": "Rahul",
        "order_id": "ORD99999",
        "issue": "Order has not arrived"
    }

    result = find_duplicate_ticket(
        new_ticket,
        existing
    )

    print(result)

    # ========================================================
    # TEST 4
    # Same order but different issue
    # Should NOT be duplicate
    # ========================================================

    print("\nTest 4 - Same order, different issue")

    existing = [
        {
            "ticket_id": "TKT-0004",
            "customer": None,
            "order_id": "ORD99999",
            "issue": "My order has not been delivered"
        }
    ]

    new_ticket = {
        "customer": None,
        "order_id": "ORD99999",
        "issue": "I want to change my delivery address"
    }

    result = find_duplicate_ticket(
        new_ticket,
        existing
    )

    print(result)

    print("\n========================================")
    print("TESTING COMPLETE")
    print("========================================")