from typing import List, Dict


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison.
    """

    return " ".join(
        text.lower()
        .strip()
        .split()
    )


def calculate_similarity(text1: str, text2: str) -> float:
    """
    Simple word-based similarity.
    """

    words1 = set(normalize_text(text1).split())
    words2 = set(normalize_text(text2).split())

    if not words1 or not words2:
        return 0.0

    intersection = words1.intersection(words2)
    union = words1.union(words2)

    return len(intersection) / len(union)


def find_duplicate_ticket(
    new_ticket: Dict,
    existing_tickets: List[Dict],
    similarity_threshold: float = 0.5
):
    """
    Check whether the new ticket is a duplicate
    of an existing ticket.
    """

    new_order_id = new_ticket.get("order_id")
    new_customer = new_ticket.get("customer")
    new_issue = new_ticket.get("issue", "")

    for ticket in existing_tickets:

        existing_order_id = ticket.get("order_id")
        existing_customer = ticket.get("customer")
        existing_issue = ticket.get("issue", "")

        # Order ID is the strongest duplicate signal
        same_order = (
            new_order_id is not None
            and existing_order_id == new_order_id
        )

        # Same customer
        same_customer = (
            new_customer is not None
            and existing_customer is not None
            and normalize_text(new_customer)
            == normalize_text(existing_customer)
        )

        # Similar issue
        similarity = calculate_similarity(
            new_issue,
            existing_issue
        )

        if same_order and same_customer and similarity >= similarity_threshold:

            return {
                "is_duplicate": True,
                "existing_ticket_id": ticket.get("ticket_id"),
                "similarity": round(similarity, 2),
                "reason": "Same customer, order and similar issue."
            }

    return {
        "is_duplicate": False,
        "existing_ticket_id": None,
        "similarity": 0.0,
        "reason": "No duplicate ticket found."
    }


if __name__ == "__main__":

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

    print("\nDuplicate Detection Result:")
    print(result)