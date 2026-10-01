"""
Integration tests for the public FastAPI flow.

They drive the application through its HTTP endpoints exactly like
the frontend does, and verify important fields instead of exact
timestamps, so the tests stay valid on any day and time.

Covered endpoints:
    GET  / (frontend chat UI - HTML)
    GET  /health (JSON API health)
    GET  /script.js, /style.css (frontend assets)
    POST /chat
    POST /tickets
"""

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.rag.answer import SAFE_FALLBACK_ANSWER


client = TestClient(app)


def post_chat(message, **overrides):
    """POST a message to /chat and return the JSON body."""

    payload = {"message": message}

    payload.update(overrides)

    response = client.post("/chat", json=payload)

    assert response.status_code == 200, response.text

    return response.json()


def post_ticket(message, **overrides):
    """POST a message to /tickets and return the JSON body."""

    payload = {"message": message}

    payload.update(overrides)

    response = client.post("/tickets", json=payload)

    assert response.status_code == 200, response.text

    return response.json()


def source_names(data):
    """Return the knowledge-base document names of a /chat answer."""

    return [
        source["filename"]
        for source in data["knowledge_base_sources"]
    ]


# ============================================================
# HEALTH CHECK
# ============================================================

def test_home_endpoint_serves_frontend():
    """GET / serves the chat UI HTML, not the JSON health response."""

    response = client.get("/")

    assert response.status_code == 200

    assert "text/html" in response.headers["content-type"]

    assert "<!DOCTYPE html>" in response.text
    assert 'id="chatBox"' in response.text
    assert '<script src="script.js"></script>' in response.text


def test_health_endpoint_reports_online():

    response = client.get("/health")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "online"
    assert "message" in body


def test_frontend_assets_are_served():

    script = client.get("/script.js")

    assert script.status_code == 200
    assert "/chat" in script.text

    style = client.get("/style.css")

    assert style.status_code == 200
    assert "chat" in style.text.lower()


def test_api_documentation_is_available():
    """
    Swagger documentation and the OpenAPI schema must be reachable,
    so every endpoint can be tested from /docs without a frontend.
    """

    assert client.get("/docs").status_code == 200

    assert client.get("/openapi.json").status_code == 200

    schema = client.get("/openapi.json").json()

    assert {"/chat", "/tickets", "/upload"} <= set(schema["paths"])


# ============================================================
# POST /chat
# ============================================================

CHAT_CASES = [
    pytest.param(
        "My order ORD20001 has not been delivered",
        "ORD20001",
        "LOW",
        480,
        "delivery_policy.txt",
        id="delivery-with-order-id"
    ),
    pytest.param(
        "The product from order ORD20002 is broken and shows ERR-500",
        "ORD20002",
        "MEDIUM",
        240,
        "troubleshooting.txt",
        id="product-error-with-order-id"
    ),
    pytest.param(
        "I was charged twice for order ORD20003",
        "ORD20003",
        "LOW",
        480,
        "payment.policy.txt",
        id="payment-with-order-id"
    ),
    pytest.param(
        "My order has not been delivered",
        None,
        "LOW",
        480,
        "delivery_policy.txt",
        id="delivery-without-order-id"
    ),
    pytest.param(
        "How long does delivery normally take?",
        None,
        "LOW",
        480,
        "delivery_policy.txt",
        id="delivery-question"
    ),
]


@pytest.mark.parametrize(
    "message,expected_order_id,expected_priority,expected_sla_minutes,"
    "expected_source",
    CHAT_CASES
)
def test_chat_endpoint_returns_expected_analysis(
    message,
    expected_order_id,
    expected_priority,
    expected_sla_minutes,
    expected_source
):
    """
    The customer message must produce the extracted order ID, the
    priority, the SLA duration and a grounded knowledge-base answer.
    """

    data = post_chat(message)

    # ----------------------------------------------------
    # Ticket information / required information
    # ----------------------------------------------------

    assert data["ticket_information"]["order_id"] == expected_order_id

    assert isinstance(data["ticket_information"]["issue"], str)

    if expected_order_id is None:

        assert data["missing_information"] == ["order_id"]
        assert data["ticket_ready"] is False

    else:

        assert data["missing_information"] == []
        assert data["ticket_ready"] is True

    # ----------------------------------------------------
    # Priority / severity / SLA (no timestamps compared)
    # ----------------------------------------------------

    assert data["priority"] == expected_priority

    assert data["severity"] in {"Low", "Medium", "High", "Critical"}

    assert data["sla"]["sla_minutes"] == expected_sla_minutes

    assert data["sla"]["status"] in {
        "WITHIN_SLA",
        "WARNING",
        "BREACHED"
    }

    # ----------------------------------------------------
    # RAG
    # ----------------------------------------------------

    assert data["rag_used"] is True

    assert source_names(data) == [expected_source]

    assert data["knowledge_base_answer"]
    assert data["knowledge_base_answer"] != SAFE_FALLBACK_ANSWER

    # ----------------------------------------------------
    # Conversation / session context
    # ----------------------------------------------------

    assert isinstance(data["conversation_context"], list)

    assert data["context_message_count"] >= 1

    assert data["language"]["language_code"] == "en"

    for field in (
        "escalation",
        "after_hours",
        "normalized_message",
        "sentiment",
        "sentiment_category"
    ):

        assert field in data


def test_chat_delivery_question_answers_3_to_7_business_days():
    """
    The delivery policy answer must come from the trusted document.
    """

    data = post_chat("How long does delivery normally take?")

    assert "3 to 7 business days" in data["knowledge_base_answer"]


def test_chat_unsupported_question_uses_safe_fallback():
    """
    A question outside the knowledge base must not invent an answer.
    """

    data = post_chat("What is the capital of France?")

    assert data["rag_used"] is False

    assert data["knowledge_base_sources"] == []

    assert data["knowledge_base_answer"] == SAFE_FALLBACK_ANSWER


def test_chat_rejects_invalid_requested_date():
    """
    Existing API behaviour: an invalid historical policy date is
    reported as an error instead of raising a 500 response.
    """

    response = client.post(
        "/chat",
        json={
            "message": "I want a refund",
            "requested_date": "not-a-date"
        }
    )

    assert response.status_code == 200

    assert "error" in response.json()


def test_chat_requires_a_message():

    response = client.post("/chat", json={})

    assert response.status_code == 422


def test_chat_response_does_not_expose_secrets():
    """
    The customer-facing response must never contain API keys or
    similar secrets.
    """

    data = post_chat("My order ORD35009 has not been delivered")

    body = str(data).lower()

    for marker in ("api_key", "apikey", "sk-", "bearer "):

        assert marker not in body


# ============================================================
# POST /tickets
# ============================================================

@pytest.mark.parametrize(
    "message,expected_skill,expected_agent",
    [
        pytest.param(
            "My order ORD35011 has not been delivered",
            "delivery",
            "Agent Rahul",
            id="delivery"
        ),
        pytest.param(
            "The product from order ORD35012 is not working and "
            "shows error code ERR-500.",
            "technical",
            "Agent Amit",
            id="product-error-regression"
        ),
        pytest.param(
            "The product from order ORD35013 is broken and shows ERR-500",
            "technical",
            "Agent Amit",
            id="product-broken"
        ),
        pytest.param(
            "I was charged twice for order ORD35014",
            "payment",
            "Agent Priya",
            id="payment"
        ),
    ]
)
def test_tickets_endpoint_routes_to_the_right_skill(
    message,
    expected_skill,
    expected_agent
):
    """
    The complete ticket flow (extraction -> priority -> routing ->
    ticket creation) must select the matching skill and agent.
    """

    data = post_ticket(message)

    assert data["ticket_created"] is True

    assert data["routing"]["required_skill"] == expected_skill

    assert data["routing"]["assigned"] is True
    assert data["routing"]["agent"] == expected_agent

    assert data["ticket"]["ticket_id"].startswith("TKT-")

    assert data["ticket"]["priority"] in {
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL"
    }

    assert data["sla"]["sla_minutes"] in {60, 120, 240, 480}

    assert data["handoff_summary"]


def test_tickets_endpoint_requires_order_id():

    data = post_ticket("My order has not been delivered")

    assert data["ticket_created"] is False

    assert data["missing_information"] == ["order_id"]


def test_tickets_endpoint_detects_duplicate_ticket():
    """
    The same order + the same issue must not create a second ticket.
    """

    message = "My order ORD35015 has not been delivered"

    first = post_ticket(message)

    assert first["ticket_created"] is True

    second = post_ticket(message)

    assert second["ticket_created"] is False
    assert second["duplicate"] is True

    assert second["duplicate_information"]["is_duplicate"] is True

    assert (
        second["duplicate_information"]["existing_ticket_id"]
        == first["ticket"]["ticket_id"]
    )


def test_tickets_endpoint_reports_issue_relations():
    """
    Existing behaviour: relations with earlier tickets are reported.
    """

    data = post_ticket(
        "The product from order ORD35016 is broken and shows ERR-500"
    )

    assert data["ticket_created"] is True

    assert isinstance(data["issue_relations"], list)

    assert data["routing"]["required_skill"] == "technical"


# ============================================================
# ISOLATED TICKET STORE
# ============================================================

@pytest.fixture()
def isolated_ticket_store():
    """
    Give a test a private, empty ticket store.

    Duplicate and relation detection compare a new ticket against the
    tickets that already exist. Restoring the original store keeps each
    test independent of the tests that ran before it.
    """

    from backend import main as backend_main

    saved_tickets = list(backend_main.tickets)

    saved_counter = backend_main.ticket_counter

    backend_main.tickets.clear()

    backend_main.ticket_counter = 900000

    try:

        yield backend_main

    finally:

        backend_main.tickets.clear()

        backend_main.tickets.extend(saved_tickets)

        backend_main.ticket_counter = saved_counter


def relations_by_ticket(data):
    """Map issue relations by the existing ticket id they describe."""

    return {
        relation["existing_ticket_id"]: relation
        for relation in data["issue_relations"]
    }


# ============================================================
# TICKET RELATIONSHIPS
# ============================================================

def test_same_category_different_order_is_related_not_duplicate(
    isolated_ticket_store
):
    """
    Customer support condition: the same issue for another order.

    The issue category matches but the order is different, so a new
    ticket must be created and reported as related to the first one
    instead of being treated as a duplicate.
    """

    first = post_ticket("My order ORD60001 has not been delivered")

    assert first["ticket_created"] is True

    second = post_ticket("My order ORD60002 has not been delivered")

    assert second["ticket_created"] is True

    # For a created ticket the endpoint reports the duplicate check
    # result as an object, while a detected duplicate answers with the
    # boolean flag `duplicate: true`.

    assert second["duplicate"]["is_duplicate"] is False

    relation = relations_by_ticket(second)[
        first["ticket"]["ticket_id"]
    ]

    assert relation["relation"] == "RELATED"

    assert relation["same_order"] is False

    assert len(isolated_ticket_store.tickets) == 2


def test_different_category_is_unrelated(isolated_ticket_store):
    """
    Customer support condition: a different issue for another order.

    Different categories must be reported as unrelated tickets.
    """

    first = post_ticket("My order ORD60003 has not been delivered")

    assert first["ticket_created"] is True

    second = post_ticket(
        "The product from order ORD60004 is broken and shows ERR-500"
    )

    assert second["ticket_created"] is True

    assert second["duplicate"]["is_duplicate"] is False

    assert second["routing"]["required_skill"] == "technical"

    relation = relations_by_ticket(second)[
        first["ticket"]["ticket_id"]
    ]

    assert relation["relation"] == "UNRELATED"


def test_repeated_submission_of_the_same_issue_creates_one_ticket(
    isolated_ticket_store
):
    """
    Customer support condition: repeated submission of the same issue.

    The chat analysis says a ticket can be created, the first ticket is
    created, and submitting the same issue again reuses the existing
    ticket.
    """

    message = "My order ORD12345 has not been delivered"

    analysis = post_chat(message)

    assert analysis["ticket_ready"] is True

    assert analysis["ticket_information"]["order_id"] == "ORD12345"

    first = post_ticket(message)

    assert first["ticket_created"] is True

    assert first["ticket"]["order_id"] == "ORD12345"

    second = post_ticket(message)

    assert second["ticket_created"] is False

    assert second["duplicate"] is True

    assert (
        second["duplicate_information"]["existing_ticket_id"]
        == first["ticket"]["ticket_id"]
    )

    assert len(isolated_ticket_store.tickets) == 1



# ============================================================
# KNOWLEDGE BASE ANSWER WITHOUT AN ORDER ID
# ============================================================

def test_chat_answers_from_knowledge_base_without_order_id():
    """
    Customer support condition: incomplete order information.

    The customer must still receive a knowledge-base answer, while the
    ticket is not created until the missing order ID is provided.
    """

    data = post_chat("My order has not been delivered")

    assert data["ticket_information"]["order_id"] is None

    assert data["ticket_ready"] is False

    assert data["missing_information"] == ["order_id"]

    assert data["rag_used"] is True

    assert data["knowledge_base_answer"]

    assert data["knowledge_base_answer"] != SAFE_FALLBACK_ANSWER

    assert "delivery_policy.txt" in source_names(data)


# ============================================================
# INPUT VALIDATION
# ============================================================

@pytest.mark.parametrize(
    "endpoint",
    [
        pytest.param("/chat", id="chat"),
        pytest.param("/tickets", id="tickets"),
    ]
)
@pytest.mark.parametrize(
    "message",
    [
        pytest.param("", id="empty"),
        pytest.param("   ", id="spaces"),
        pytest.param("\n\t  ", id="newlines-and-tabs"),
    ]
)
def test_blank_message_is_rejected(endpoint, message):
    """
    Customer support condition: empty message.

    An empty or whitespace-only message must be rejected with a clear
    validation error instead of running the whole analysis pipeline.
    """

    response = client.post(endpoint, json={"message": message})

    assert response.status_code == 422

    assert "Message must not be empty" in response.text


@pytest.mark.parametrize(
    "endpoint",
    [
        pytest.param("/chat", id="chat"),
        pytest.param("/tickets", id="tickets"),
    ]
)
def test_missing_message_field_is_rejected(endpoint):
    """The message field is required by both endpoints."""

    response = client.post(endpoint, json={"customer_id": "abc"})

    assert response.status_code == 422

    assert "message" in response.text


# ============================================================
# UNEXPECTED BACKEND FAILURES
# ============================================================

def test_unexpected_backend_failure_returns_clean_json(monkeypatch):
    """
    Customer support condition: backend/API failure.

    An unexpected exception must be logged on the server and answered
    with a controlled JSON error. A stack trace or internal detail must
    never reach the customer. The frontend behaviour for the same case
    is verified by tests/frontend_harness.js.
    """

    from backend import main as backend_main

    def exploding_answer(*args, **kwargs):

        raise RuntimeError("simulated internal failure")

    monkeypatch.setattr(
        backend_main,
        "generate_grounded_answer",
        exploding_answer
    )

    # raise_server_exceptions=False emulates a real ASGI server that
    # hands the failure to the global exception handler.

    failing_client = TestClient(
        backend_main.app,
        raise_server_exceptions=False
    )

    response = failing_client.post(
        "/chat",
        json={"message": "My order ORD70001 has not been delivered"}
    )

    assert response.status_code == 500

    body = response.json()

    assert body["error"] == "internal_server_error"

    assert "unexpected error" in body["message"].lower()

    assert "Traceback" not in response.text

    assert "RuntimeError" not in response.text

    assert "simulated internal failure" not in response.text


# ============================================================
# RESPONSE TIME
# ============================================================

RESPONSE_TIME_LIMIT_SECONDS = 10


def test_chat_and_ticket_requests_complete_within_the_limit():
    """
    Requirement: every request must finish within 10 seconds.

    The measured calls include routing, priority, SLA, ticket creation
    and the knowledge-base lookup.
    """

    started = time.perf_counter()

    post_chat("My order ORD80001 has not been delivered")

    chat_duration = time.perf_counter() - started

    assert chat_duration < RESPONSE_TIME_LIMIT_SECONDS

    started = time.perf_counter()

    post_ticket("My order ORD80002 has not been delivered")

    ticket_duration = time.perf_counter() - started

    assert ticket_duration < RESPONSE_TIME_LIMIT_SECONDS


# ============================================================
# COMPLETE CUSTOMER WORKFLOW
# ============================================================

INVOICE_PDF = Path("data/uploads/processed/test_invoice.pdf")


@pytest.mark.skipif(
    not INVOICE_PDF.exists(),
    reason="PDF fixture data/uploads/processed/test_invoice.pdf is missing."
)
def test_upload_chat_and_ticket_workflow_for_the_same_order(
    isolated_ticket_store
):
    """
    Customer support condition: evidence attached to a complaint.

    The complete flow a customer follows: upload an invoice, ask about
    the order, get a knowledge-base answer, create a ticket, and see a
    duplicate instead of a second ticket when the issue is resubmitted.
    """

    message = "My order ORD12345 has not been delivered"

    with INVOICE_PDF.open("rb") as invoice:

        upload = client.post(
            "/upload",
            files={"file": ("order_invoice.pdf", invoice, "application/pdf")},
            data={"customer_message": message}
        )

    assert upload.status_code == 200

    uploaded = upload.json()

    assert uploaded["success"] is True

    assert "ORD12345" in uploaded["extracted_information"]["order_ids"]

    assert (
        uploaded["extracted_information"]["comparison"]["status"]
        == "MATCH"
    )

    analysis = post_chat(message)

    assert analysis["ticket_ready"] is True

    assert analysis["ticket_information"]["order_id"] == "ORD12345"

    assert analysis["knowledge_base_answer"]

    ticket = post_ticket(message)

    assert ticket["ticket_created"] is True

    assert ticket["ticket"]["order_id"] == "ORD12345"

    assert ticket["routing"]["required_skill"] == "delivery"

    again = post_ticket(message)

    assert again["ticket_created"] is False

    assert len(isolated_ticket_store.tickets) == 1

