"""
Automated condition tests for the GenAI Customer Support pipeline.

The tests call the existing implementation exactly as it is used by
the FastAPI application (no invented signatures):

    extract_ticket_information / check_missing_information
    calculate_priority
    find_duplicate_ticket
    compare_issues
    calculate_sla
    determine_required_skill / route_ticket
    generate_grounded_answer
    multimodal OCR extractors and conflict detection

Parametrization is used wherever the same behaviour is verified for
more than one input, so conditions are documented instead of being
duplicated in separate functions.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.chatbot.sentiment import analyze_sentiment
from backend.main import app
from backend.multimodal.conflict import compare_file_with_message
from backend.multimodal.ocr import (
    extract_amounts,
    extract_dates,
    extract_error_codes,
    extract_order_ids,
    extract_text
)
from backend.rag.answer import (
    SAFE_FALLBACK_ANSWER,
    generate_grounded_answer
)
from backend.tickets.duplicate import find_duplicate_ticket
from backend.tickets.extractor import (
    check_missing_information,
    extract_ticket_information
)
from backend.tickets.issue_relation import compare_issues
from backend.tickets.priority import calculate_priority
from backend.tickets.routing import (
    determine_required_skill,
    route_ticket
)
from backend.tickets.sla import calculate_sla


client = TestClient(app)


# Test fixtures that already exist in the repository. They are never
# modified, only read.
INVOICE_PDF = Path("data/uploads/processed/test_invoice.pdf")


def ask(message, **overrides):
    """
    Send a message to POST /chat and return the JSON body.

    Used for the conditions that are produced by the whole pipeline
    (sentiment -> severity -> priority) instead of a single function.
    """

    payload = {"message": message}

    payload.update(overrides)

    response = client.post("/chat", json=payload)

    assert response.status_code == 200, response.text

    return response.json()


# ============================================================
# A. TICKET INFORMATION EXTRACTION
# ============================================================

@pytest.mark.parametrize(
    "message,expected_order_id",
    [
        (
            "My order ORD10001 has not been delivered.",
            "ORD10001"
        ),
        (
            "The product from order ORD10002 is not working "
            "and shows error code ERR-500.",
            "ORD10002"
        ),
        (
            "I was charged twice for order ORD10003.",
            "ORD10003"
        ),
        (
            "My order ORD-10004 has not arrived yet.",
            "ORD10004"
        ),
    ],
    ids=["delivery", "product-issue", "payment-issue", "hyphenated"]
)
def test_order_id_is_extracted(message, expected_order_id):
    """
    Conditions 1-3: order IDs are extracted from delivery, product
    and payment messages.
    """

    ticket_info = extract_ticket_information(message)

    assert ticket_info["order_id"] == expected_order_id

    assert isinstance(ticket_info["issue"], str)
    assert ticket_info["issue"].strip()

    assert check_missing_information(ticket_info) == []


@pytest.mark.parametrize(
    "text,expected_error_codes",
    [
        (
            "The product from order ORD10002 is not working and "
            "shows error code ERR-500.",
            ["ERR-500"]
        ),
        (
            "Error Code: E1024 while checking out",
            ["E1024"]
        ),
        (
            "Everything works fine, thank you.",
            []
        ),
    ],
    ids=["err-500", "code-with-error-label", "no-error-code"]
)
def test_error_code_extraction(text, expected_error_codes):
    """
    Condition 4: error codes are extracted by the existing
    multimodal OCR extractor (error codes live in the multimodal
    layer, not in backend/tickets/extractor.py).
    """

    assert extract_error_codes(text) == expected_error_codes


@pytest.mark.parametrize(
    "message",
    [
        "My laptop has not arrived.",
        "My order issue is not resolved.",
        "The product is broken and shows ERR-500.",
    ],
    ids=["no-id", "order-word-without-digits", "product-without-order"]
)
def test_missing_order_id_is_reported(message):
    """
    Condition 5: a message without a real order ID must not
    invent one, and the missing information must be reported.
    """

    ticket_info = extract_ticket_information(message)

    assert ticket_info["order_id"] is None

    assert check_missing_information(ticket_info) == ["order_id"]


# ============================================================
# B. PRIORITY CONDITIONS
# ============================================================

@pytest.mark.parametrize(
    "severity,sentiment,waiting_minutes,customer_impact,expected",
    [
        # Condition 6 - a calm delivery request stays LOW
        ("Low", "Neutral", 0, "Low", "LOW"),
        # Condition 7 - a negative issue is MEDIUM
        ("Medium", "Negative", 0, "Medium", "MEDIUM"),
        # Condition 8 - a high severity issue is HIGH
        ("High", "Urgent", 0, "Medium", "HIGH"),
        # Condition 9 - a frustrated customer waiting for help is HIGH
        ("High", "Frustrated", 30, "Medium", "HIGH"),
        # Condition 10 - an urgent customer with critical impact
        ("Critical", "Urgent", 60, "Critical", "CRITICAL"),
    ],
    ids=[
        "low",
        "medium",
        "high",
        "frustrated",
        "urgent"
    ]
)
def test_priority_calculation(
    severity,
    sentiment,
    waiting_minutes,
    customer_impact,
    expected
):
    """
    Conditions 6-10: priority is derived from severity, sentiment,
    waiting time and customer impact.
    """

    result = calculate_priority(
        severity=severity,
        sentiment=sentiment,
        waiting_minutes=waiting_minutes,
        customer_impact=customer_impact
    )

    assert result["priority"] == expected

    assert isinstance(result["score"], int)


@pytest.mark.parametrize(
    "message,expected_priority",
    [
        (
            "My order ORD10010 has not been delivered.",
            "LOW"
        ),
        (
            "The product from order ORD10011 is not working and "
            "shows error code ERR-500.",
            "MEDIUM"
        ),
        (
            "I am extremely frustrated! My order ORD10012 has not "
            "been delivered after three weeks.",
            "HIGH"
        ),
        (
            "This is urgent! My order ORD10013 has not been "
            "delivered and I need it immediately!",
            "HIGH"
        ),
    ],
    ids=["low", "medium", "frustrated", "urgent"]
)
def test_priority_through_chat_pipeline(message, expected_priority):
    """
    Conditions 6-10 verified through the real pipeline
    (analyze_sentiment -> severity -> calculate_priority) instead of
    re-implementing the severity mapping inside the test.
    """

    data = ask(message)

    assert data["priority"] == expected_priority

    assert data["severity"] in {"Low", "Medium", "High", "Critical"}

    assert data["sentiment_category"] == analyze_sentiment(
        message
    )["category"]


# ============================================================
# C. DUPLICATE DETECTION
# ============================================================

DUPLICATE_EXISTING_TICKET = {
    "ticket_id": "TKT-0001",
    "customer": None,
    "order_id": "ORD10020",
    "issue": "Order has not been delivered"
}


@pytest.mark.parametrize(
    "new_ticket,expected_is_duplicate",
    [
        # Condition 11 - same order + same issue
        (
            {
                "customer": None,
                "order_id": "ORD10020",
                "issue": "Order has not been delivered yet"
            },
            True
        ),
        # Condition 12 - different order
        (
            {
                "customer": None,
                "order_id": "ORD10099",
                "issue": "Order has not been delivered"
            },
            False
        ),
        # Condition 13 - same order but different issue
        (
            {
                "customer": None,
                "order_id": "ORD10020",
                "issue": "I want to change my delivery address"
            },
            False
        ),
    ],
    ids=["same-order-same-issue", "different-order", "different-issue"]
)
def test_duplicate_detection(new_ticket, expected_is_duplicate):
    """
    Conditions 11-13: duplicates require the same order and a
    similar issue.
    """

    result = find_duplicate_ticket(
        new_ticket,
        [DUPLICATE_EXISTING_TICKET]
    )

    assert result["is_duplicate"] is expected_is_duplicate

    if expected_is_duplicate:

        assert result["existing_ticket_id"] == "TKT-0001"
        assert result["similarity"] >= 0.5

    else:

        assert result["existing_ticket_id"] is None


# ============================================================
# D. ISSUE RELATIONSHIPS
# ============================================================

@pytest.mark.parametrize(
    "issue1,issue2,expected_relation,expected_category1,expected_category2",
    [
        # Condition 14
        (
            "My order has not been delivered",
            "Order delivery is delayed",
            "RELATED",
            "delivery",
            "delivery"
        ),
        # Condition 15
        (
            "The product is broken",
            "Product shows error code ERR-500",
            "RELATED",
            "product",
            "product"
        ),
        # Condition 16
        (
            "I was charged twice",
            "I need a refund",
            "RELATED",
            "payment",
            "payment"
        ),
        # Condition 17
        (
            "My order has not been delivered",
            "The product is broken",
            "UNRELATED",
            "delivery",
            "product"
        ),
        # Condition 18
        (
            "I was charged twice",
            "Delivery is delayed",
            "UNRELATED",
            "payment",
            "delivery"
        ),
    ],
    ids=[
        "delivery-delivery",
        "product-product",
        "payment-payment",
        "delivery-product",
        "payment-delivery"
    ]
)
def test_issue_relationships(
    issue1,
    issue2,
    expected_relation,
    expected_category1,
    expected_category2
):
    """
    Conditions 14-18: issues in the same support category are
    RELATED, issues in different categories are UNRELATED.
    """

    result = compare_issues(
        issue1,
        issue2,
        "ORD10030",
        "ORD10030"
    )

    assert result["relation"] == expected_relation

    assert result["issue1_category"] == expected_category1
    assert result["issue2_category"] == expected_category2

    assert result["same_order"] is True


# ============================================================
# E. SLA
# ============================================================

@pytest.mark.parametrize(
    "priority,expected_minutes",
    [
        # Condition 19
        ("LOW", 480),
        # Condition 20
        ("MEDIUM", 240),
        # Condition 21
        ("HIGH", 120),
        # Existing behaviour that must not change
        ("CRITICAL", 60),
    ],
    ids=["low", "medium", "high", "critical"]
)
def test_sla_minutes_per_priority(priority, expected_minutes):
    """
    Conditions 19-21: SLA duration in business minutes per priority.

    Only the duration is asserted, never a timestamp, so the test is
    independent of the day and time it runs.
    """

    result = calculate_sla(priority)

    assert result["sla_minutes"] == expected_minutes

    assert result["status"] in {"WITHIN_SLA", "WARNING", "BREACHED"}

    for field in ("sla_start", "warning_time", "deadline"):

        assert isinstance(result[field], str)


# ============================================================
# F. ROUTING
# ============================================================

@pytest.mark.parametrize(
    "issue,expected_skill,expected_agent",
    [
        # Condition 22 - delivery
        (
            "My order ORD10040 has not been delivered",
            "delivery",
            "Agent Rahul"
        ),
        (
            "My order is delayed",
            "delivery",
            "Agent Rahul"
        ),
        # Condition 23 - product / technical / error code
        (
            "The product from order ORD10004 is not working and "
            "shows error code ERR-500.",
            "technical",
            "Agent Amit"
        ),
        (
            "Product is broken",
            "technical",
            "Agent Amit"
        ),
        (
            "The device shows ERR-500",
            "technical",
            "Agent Amit"
        ),
        # Condition 24 - payment
        (
            "I was charged twice for order ORD10043",
            "payment",
            "Agent Priya"
        ),
        (
            "I need a refund for my order",
            "payment",
            "Agent Priya"
        ),
    ],
    ids=[
        "delivery-order",
        "delivery-delayed",
        "technical-product-error",
        "technical-broken-product",
        "technical-error-code",
        "payment-charged-twice",
        "payment-refund"
    ]
)
def test_ticket_routing(issue, expected_skill, expected_agent):
    """
    Conditions 22-24: the required skill and the assigned agent for
    delivery, technical/product and payment tickets.
    """

    result = route_ticket(
        issue=issue,
        priority="MEDIUM",
        support_queue="NORMAL_SUPPORT"
    )

    assert result["required_skill"] == expected_skill

    assert result["assigned"] is True
    assert result["agent"] == expected_agent


def test_product_error_is_not_routed_to_delivery():
    """
    Regression test for the reported bug.

    "The product from order ORD10004 is not working and shows error
    code ERR-500." used to match the bare "order" delivery keyword
    and was routed to the delivery queue (Agent Rahul) even though
    the message describes a product defect.
    """

    issue = (
        "The product from order ORD10004 is not working and shows "
        "error code ERR-500."
    )

    assert "order" in issue.lower()

    assert determine_required_skill(issue) == "technical"

    result = route_ticket(
        issue=issue,
        priority="HIGH",
        support_queue="NORMAL_SUPPORT"
    )

    assert result["required_skill"] == "technical"
    assert result["agent"] == "Agent Amit"


@pytest.mark.parametrize(
    "message",
    [
        "I cannot login to my account",
        "Someone hacked my account",
        "I forgot my password",
        "My account is locked",
    ],
    ids=["login", "hacked", "password", "locked"]
)
def test_account_keywords_route_to_account_skill(message):
    """
    Account/login messages must reach the account skill. The only
    account agent (Agent Neha) is currently unavailable, so the
    ticket is queued without an agent instead of being misrouted.
    """

    result = route_ticket(
        issue=message,
        priority="HIGH",
        support_queue="NORMAL_SUPPORT"
    )

    assert result["required_skill"] == "account"

    assert result["assigned"] is False
    assert result["agent"] is None
    assert result["queue"] == "NORMAL_SUPPORT"


def test_generic_order_question_still_reaches_delivery():
    """
    The bare "order" fallback was kept, so a generic order question
    still reaches the delivery/order team instead of "general".
    """

    assert determine_required_skill(
        "What is my order status?"
    ) == "delivery"

    result = route_ticket(
        issue="Please continue with my order issue",
        priority="LOW",
        support_queue="NORMAL_SUPPORT"
    )

    assert result["required_skill"] == "delivery"
    assert result["agent"] == "Agent Rahul"


def test_unrelated_issue_is_general():
    """
    A message without any support keyword remains "general" and is
    not force-assigned to a specialist.
    """

    result = route_ticket(
        issue="Completely unrelated request",
        priority="LOW",
        support_queue="NORMAL_SUPPORT"
    )

    assert result["required_skill"] == "general"
    assert result["assigned"] is False


def test_on_call_routing_is_unchanged():
    """
    Existing ON_CALL routing for high-risk security tickets must keep
    working.
    """

    result = route_ticket(
        issue="Someone hacked my account",
        priority="CRITICAL",
        support_queue="ON_CALL"
    )

    assert result["required_skill"] == "account"
    assert result["queue"] == "ON_CALL"
    assert result["assigned"] is True
    assert result["agent"] == "Agent Neha"


# ============================================================
# G. RAG / KNOWLEDGE BASE
# ============================================================

def answer_from_knowledge_base(query):
    """
    Call the existing grounded-answer function directly (the same
    function POST /chat uses).
    """

    return generate_grounded_answer(query)


def test_delivery_question_uses_delivery_policy():
    """
    Condition 25: a delivery question is answered from the trusted
    delivery policy document.
    """

    result = answer_from_knowledge_base(
        "How long does delivery normally take?"
    )

    assert result["rag_used"] is True

    assert [
        source["filename"]
        for source in result["sources"]
    ] == ["delivery_policy.txt"]

    assert "3 to 7 business days" in result["answer"]

    assert result["answer"] != SAFE_FALLBACK_ANSWER


@pytest.mark.parametrize(
    "question",
    [
        "What is the capital of France?",
        "Tell me something unrelated that is not in the knowledge base.",
    ],
    ids=["unsupported-topic", "unsupported-sentence"]
)
def test_unsupported_question_does_not_invent_an_answer(question):
    """
    Condition 26: when the knowledge base has no trusted evidence,
    the safe fallback answer is returned instead of an invented one.
    """

    result = answer_from_knowledge_base(question)

    assert result["rag_used"] is False

    assert result["sources"] == []

    assert result["answer"] == SAFE_FALLBACK_ANSWER

    assert result["chunks_retrieved"] == 0


# ============================================================
# H. MULTIMODAL
# ============================================================

invoice_fixture_required = pytest.mark.skipif(
    not INVOICE_PDF.exists(),
    reason="PDF fixture data/uploads/processed/test_invoice.pdf is missing."
)


@invoice_fixture_required
def test_invoice_ocr_extracts_order_id():
    """
    Condition 27: the PDF invoice fixture exposes its order ID.
    """

    extracted_text = extract_text(INVOICE_PDF)

    assert extract_order_ids(extracted_text) == ["ORD12345"]


@invoice_fixture_required
def test_invoice_ocr_extracts_amount():
    """
    Condition 28: the invoice amount is extracted from the PDF.
    """

    amounts = extract_amounts(
        extract_text(INVOICE_PDF)
    )

    assert amounts

    assert "29,999" in amounts[0]


def test_amount_extraction_patterns():
    """
    Condition 28 (unit): the existing amount extractor recognises
    labelled amounts and ignores text without an amount.
    """

    assert extract_amounts("Amount: Rs. 29,999") == ["Rs. 29,999"]

    assert extract_amounts("No money mentioned here") == []


@invoice_fixture_required
def test_invoice_ocr_extracts_error_code():
    """
    Condition 29: the error code is extracted from the invoice PDF.
    """

    assert extract_error_codes(
        extract_text(INVOICE_PDF)
    ) == ["ERR-500"]


@invoice_fixture_required
def test_invoice_ocr_extracts_order_date():
    """
    Existing behaviour that must not regress: the invoice date is
    extracted together with the other fields.
    """

    assert extract_dates(
        extract_text(INVOICE_PDF)
    ) == ["2026-09-20"]


def test_matching_message_and_file_order_ids():
    """
    Condition 30: matching message/file order IDs produce MATCH.
    """

    result = compare_file_with_message(
        "My order ORD12345 is damaged.",
        {"order_ids": ["ORD12345"]}
    )

    assert result["status"] == "MATCH"

    assert result["conflict"] is False

    assert result["message_order_ids"] == ["ORD12345"]
    assert result["file_order_ids"] == ["ORD12345"]


def test_conflicting_message_and_file_order_ids():
    """
    Condition 31: different message/file order IDs produce CONFLICT.
    """

    result = compare_file_with_message(
        "My order ORD12345 is damaged.",
        {"order_ids": ["ORD99999"]}
    )

    assert result["status"] == "CONFLICT"

    assert result["conflict"] is True

    assert result["conflicts"][0]["field"] == "order_id"


def test_missing_order_id_means_no_comparison():
    """
    Condition 32: without an order ID there is nothing to compare.
    """

    result = compare_file_with_message(
        "Please check the attached invoice.",
        {"order_ids": ["ORD12345"]}
    )

    assert result["status"] == "NO_COMPARISON"

    assert result["conflict"] is False
