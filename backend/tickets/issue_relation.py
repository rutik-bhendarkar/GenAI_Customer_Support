from typing import Dict


# ==========================================
# ISSUE CATEGORIES
# ==========================================

ISSUE_CATEGORIES = {
    "delivery": [
        "delivery",
        "delivered",
        "arrived",
        "not arrived",
        "not delivered",
        "late",
        "delayed",
        "shipping",
        "shipment",
        "tracking"
    ],

    "payment": [
        "payment",
        "paid",
        "charged",
        "charge",
        "refund",
        "duplicate payment",
        "charged twice",
        "transaction"
    ],

    "account": [
        "account",
        "hacked",
        "hack",
        "password",
        "login",
        "logged in",
        "unauthorized",
        "security"
    ],

    "product": [
        "product",
        "damaged",
        "broken",
        "not working",
        "defective",
        "screen",
        "battery",
        "keyboard",
        "hardware"
    ]
}


# ==========================================
# DETERMINE ISSUE CATEGORY
# ==========================================

def determine_issue_category(issue: str) -> str:

    text = issue.lower()

    for category, keywords in ISSUE_CATEGORIES.items():

        for keyword in keywords:

            if keyword in text:
                return category

    return "general"


# ==========================================
# COMPARE TWO ISSUES
# ==========================================

def compare_issues(
    issue1: str,
    issue2: str,
    order_id1: str = None,
    order_id2: str = None
) -> Dict:

    category1 = determine_issue_category(issue1)

    category2 = determine_issue_category(issue2)

    # Same issue category
    same_category = category1 == category2

    # Same order
    same_order = (
        order_id1 is not None
        and order_id2 is not None
        and order_id1 == order_id2
    )

    if same_category and same_order:

        relation = "RELATED"

        reason = (
            "Issues belong to the same category "
            "and are associated with the same order."
        )

    elif same_category:

        relation = "RELATED"

        reason = (
            "Issues belong to the same support category."
        )

    else:

        relation = "UNRELATED"

        reason = (
            "Issues belong to different support categories."
        )

    return {
        "relation": relation,
        "issue1_category": category1,
        "issue2_category": category2,
        "same_order": same_order,
        "reason": reason
    }


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    print("\nTest 1 - Related delivery issues")

    result = compare_issues(
        "Order has not arrived",
        "Delivery is delayed",
        "ORD12345",
        "ORD12345"
    )

    print(result)


    print("\nTest 2 - Unrelated payment issue")

    result = compare_issues(
        "Order has not arrived",
        "Customer was charged twice",
        "ORD12345",
        "ORD12345"
    )

    print(result)


    print("\nTest 3 - Same category different orders")

    result = compare_issues(
        "Order is delayed",
        "Another order has not arrived",
        "ORD12345",
        "ORD99999"
    )

    print(result)