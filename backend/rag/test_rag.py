from datetime import date

from backend.rag.answer import (
    generate_grounded_answer
)


def run_test(name, condition):
    if condition:
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name}")


print("=" * 60)
print("TASK 4 - FINAL RAG TEST SUITE")
print("=" * 60)


# ============================================================
# TEST 1 - CURRENT POLICY
# ============================================================

result = generate_grounded_answer(
    "What is the refund period?"
)

run_test(
    "Current refund policy is retrieved",
    result["sources"]
    and result["sources"][0]["version"] == "2.0"
)


# ============================================================
# TEST 2 - DELIVERY
# ============================================================

result = generate_grounded_answer(
    "How long does delivery take?"
)

run_test(
    "Delivery policy is retrieved",
    result["sources"]
    and result["sources"][0]["filename"]
    == "delivery_policy.txt"
)


# ============================================================
# TEST 3 - PAYMENT
# ============================================================

result = generate_grounded_answer(
    "What should I do about a duplicate payment?"
)

run_test(
    "Payment policy is retrieved",
    result["sources"]
    and result["sources"][0]["filename"]
    == "payment.policy.txt"
)


# ============================================================
# TEST 4 - UNSUPPORTED QUESTION
# ============================================================

result = generate_grounded_answer(
    "What is the weather today?"
)

run_test(
    "Unsupported question is refused",
    result["sources"] == []
)


# ============================================================
# TEST 5 - HISTORICAL POLICY
# ============================================================

historical_date = date(
    2026,
    6,
    1
)

result = generate_grounded_answer(
    "What is the refund period?",
    requested_date=historical_date
)

run_test(
    "Historical policy uses version 1.0",
    result["sources"]
    and result["sources"][0]["version"] == "1.0"
)


# ============================================================
# TEST 6 - PUBLIC ACCESS CONTROL
# ============================================================

result = generate_grounded_answer(
    "What is the internal administrative information?",
    user_role="PUBLIC"
)

run_test(
    "PUBLIC user cannot access restricted policy",
    result["sources"] == []
)


# ============================================================
# TEST 7 - ADMIN ACCESS
# ============================================================

result = generate_grounded_answer(
    "What is the internal administrative information?",
    user_role="ADMIN"
)

print(
    "\nADMIN access result:",
    result["sources"]
)


# ============================================================
# FINAL RESULT
# ============================================================

print("\n" + "=" * 60)
print("RAG TEST SUITE COMPLETED")
print("=" * 60)