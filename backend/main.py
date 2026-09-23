from datetime import date

from fastapi import FastAPI
from pydantic import BaseModel


# ============================================================
# TASK 1 - SENTIMENT
# ============================================================

from backend.chatbot.sentiment import analyze_sentiment


# ============================================================
# TASK 2 - TICKETS
# ============================================================

from backend.tickets.models import SupportTicket

from backend.tickets.extractor import (
    extract_ticket_information,
    check_missing_information
)

from backend.tickets.priority import calculate_priority
from backend.tickets.routing import route_ticket
from backend.tickets.sla import calculate_sla
from backend.tickets.escalation import check_escalation
from backend.tickets.duplicate import find_duplicate_ticket
from backend.tickets.issue_relation import compare_issues
from backend.tickets.handoff import generate_handoff_summary
from backend.tickets.after_hours import determine_support_queue


# ============================================================
# TASK 4 - RAG
# ============================================================

from backend.rag.answer import generate_grounded_answer


# ============================================================
# TASK 6 - MULTILINGUAL
# ============================================================

from backend.multilingual.language import (
    detect_language,
    requires_language_clarification
)

from backend.multilingual.normalization import normalize_message
from backend.multilingual.context import ConversationContext
from backend.multilingual.session import SessionManager


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="GenAI Customer Support",
    description="AI-powered customer support chatbot",
    version="1.0.0"
)


# ============================================================
# REQUEST MODEL
# ============================================================

class ChatRequest(BaseModel):

    # Customer message
    message: str

    # Customer/session identifier
    customer_id: str = "default_customer"

    # RAG access level
    user_role: str = "PUBLIC"

    # Optional historical policy date
    requested_date: str | None = None


# ============================================================
# TEMPORARY TICKET STORAGE
# ============================================================

tickets = []

ticket_counter = 1


# ============================================================
# TASK 6 - MULTILINGUAL SESSION STORAGE
# ============================================================

# Each customer gets a separate session.
session_manager = SessionManager()

# Store ConversationContext separately for each customer.
conversation_contexts = {}


def get_customer_context(customer_id):
    """
    Return the conversation context for a customer.

    Each customer has an isolated conversation history.
    """

    if customer_id not in conversation_contexts:

        conversation_contexts[customer_id] = ConversationContext(
            max_messages=10
        )

    return conversation_contexts[customer_id]


# ============================================================
# HOME API
# ============================================================

@app.get("/")
def home():

    return {
        "status": "online",
        "message": "GenAI Customer Support API is running"
    }


# ============================================================
# CHAT API
# ============================================================

@app.post("/chat")
def chat(request: ChatRequest):

    # ========================================================
    # TASK 6 - MULTILINGUAL PROCESSING
    # ========================================================

    # Get/create customer session
    if request.customer_id not in session_manager.sessions:

        session_manager.create_session(
            request.customer_id
        )

    # Get isolated conversation context
    context_manager = get_customer_context(
        request.customer_id
    )

    # --------------------------------------------------------
    # 1. Detect language
    # --------------------------------------------------------

    language_result = detect_language(
        request.message
    )

    # --------------------------------------------------------
    # 2. Check language confidence
    # --------------------------------------------------------

    clarification_required = requires_language_clarification(
        language_result
    )

    # --------------------------------------------------------
    # 3. Normalize message
    # --------------------------------------------------------

    normalized_message = normalize_message(
        request.message
    )

    # --------------------------------------------------------
    # 4. Store conversation message
    # --------------------------------------------------------

    context_manager.add_message(
        "customer",
        request.message
    )

    # --------------------------------------------------------
    # 5. Update session activity
    # --------------------------------------------------------

    session_manager.update_activity(
        request.customer_id
    )

    # --------------------------------------------------------
    # 6. Get session status
    # --------------------------------------------------------

    session_status = session_manager.check_session_status(
        request.customer_id
    )

    # ========================================================
    # TASK 2 - EXTRACT TICKET INFORMATION
    # ========================================================

    ticket_info = extract_ticket_information(
        request.message
    )

    # ========================================================
    # CHECK MISSING INFORMATION
    # ========================================================

    missing_information = check_missing_information(
        ticket_info
    )

    # ========================================================
    # TASK 1 - SENTIMENT ANALYSIS
    # ========================================================

    sentiment_result = analyze_sentiment(
        request.message
    )

    # ========================================================
    # TRACK UNRESOLVED NEGATIVE CONVERSATION
    # ========================================================

    if sentiment_result["sentiment"] == "NEGATIVE":

        session_manager.start_unresolved(
            request.customer_id
        )

    elif sentiment_result["sentiment"] == "POSITIVE":

        session_manager.clear_unresolved(
            request.customer_id
        )

    unresolved_minutes = session_manager.get_unresolved_minutes(
        request.customer_id
    )

    # ========================================================
    # DETERMINE SEVERITY
    # ========================================================

    if sentiment_result["high_risk"]:

        severity = "Critical"

    elif sentiment_result["category"] in [
        "Urgent",
        "Frustrated"
    ]:

        severity = "High"

    elif sentiment_result["sentiment"] == "NEGATIVE":

        severity = "Medium"

    else:

        severity = "Low"

    # ========================================================
    # CALCULATE PRIORITY
    # ========================================================

    priority_result = calculate_priority(
        severity=severity,
        sentiment=sentiment_result["category"],
        waiting_minutes=0,
        customer_impact="Medium"
    )

    # ========================================================
    # TASK 2 - SLA
    # ========================================================

    sla_result = calculate_sla(
        priority=priority_result["priority"]
    )

    # ========================================================
    # TASK 1 - ESCALATION
    # ========================================================

    escalation_result = check_escalation(
        sla_result=sla_result,
        high_risk=sentiment_result["high_risk"],
        unresolved_minutes=unresolved_minutes
    )

    # ========================================================
    # ADD ESCALATION CONVERSATION SUMMARY
    # ========================================================

    if escalation_result["escalated"]:

        escalation_result["conversation_summary"] = (
            f"Customer {request.customer_id} reported: "
            f"{request.message}. "
            f"Sentiment: {sentiment_result['category']}. "
            f"Priority: {priority_result['priority']}. "
            f"Unresolved for {unresolved_minutes} minutes."
        )

    # ========================================================
    # AFTER-HOURS SUPPORT QUEUE
    # ========================================================

    after_hours_result = determine_support_queue(
        priority=priority_result["priority"],
        high_risk=sentiment_result["high_risk"]
    )

    # ========================================================
    # TASK 4 - RAG KNOWLEDGE ASSISTANT
    # ========================================================

    requested_date = None

    if request.requested_date:

        try:

            requested_date = date.fromisoformat(
                request.requested_date
            )

        except ValueError:

            return {
                "error": (
                    "Invalid requested_date format. "
                    "Use YYYY-MM-DD."
                )
            }

    rag_result = generate_grounded_answer(
        query=request.message,
        user_role=request.user_role,
        requested_date=requested_date
    )

    # ========================================================
    # RETURN CHATBOT RESULT
    # ========================================================

    return {

        # ----------------------------------------------------
        # Original message
        # ----------------------------------------------------

        "message": request.message,

        # ====================================================
        # TASK 6 - MULTILINGUAL
        # ====================================================

        "language": language_result,

        "language_clarification_required":
            clarification_required,

        "normalized_message":
            normalized_message,

        "conversation_context":
            context_manager.get_history(),

        "context_message_count":
            context_manager.get_message_count(),

        "session":
            session_status,

        # ====================================================
        # TASK 2 - TICKET
        # ====================================================

        "ticket_information":
            ticket_info,

        # ====================================================
        # TASK 1 - SENTIMENT
        # ====================================================

        "sentiment":
            sentiment_result["sentiment"],

        "sentiment_category":
            sentiment_result["category"],

        "confidence":
            sentiment_result["confidence"],

        # ====================================================
        # SEVERITY
        # ====================================================

        "severity":
            severity,

        # ====================================================
        # PRIORITY
        # ====================================================

        "priority":
            priority_result["priority"],

        "priority_score":
            priority_result["score"],

        # ====================================================
        # UNRESOLVED CONVERSATION
        # ====================================================

        "unresolved_minutes":
            unresolved_minutes,

        # ====================================================
        # SLA
        # ====================================================

        "sla":
            sla_result,

        # ====================================================
        # ESCALATION
        # ====================================================

        "escalation":
            escalation_result,

        # ====================================================
        # AFTER-HOURS
        # ====================================================

        "after_hours":
            after_hours_result,

        # ====================================================
        # MISSING INFORMATION
        # ====================================================

        "missing_information":
            missing_information,

        "ticket_ready":
            len(missing_information) == 0,

        # ====================================================
        # TASK 4 - RAG
        # ====================================================

        "knowledge_base_answer":
            rag_result["answer"],

        "knowledge_base_sources":
            rag_result["sources"],

        "rag_used":
            len(rag_result["sources"]) > 0
    }


# ============================================================
# CREATE SUPPORT TICKET
# ============================================================

@app.post("/tickets")
def create_ticket(request: ChatRequest):

    global ticket_counter

    # ========================================================
    # 1. EXTRACT INFORMATION
    # ========================================================

    ticket_info = extract_ticket_information(
        request.message
    )

    # ========================================================
    # 2. CHECK MISSING INFORMATION
    # ========================================================

    missing_information = check_missing_information(
        ticket_info
    )

    if missing_information:

        return {

            "ticket_created": False,

            "missing_information":
                missing_information,

            "message":
                "Please provide the missing information "
                "before creating the ticket."
        }

    # ========================================================
    # 3. DUPLICATE TICKET DETECTION
    # ========================================================

    new_ticket_data = {

        "customer":
            ticket_info["customer"],

        "order_id":
            ticket_info["order_id"],

        "issue":
            ticket_info["issue"]
    }

    existing_ticket_data = [

        ticket.model_dump()

        for ticket in tickets
    ]

    # ========================================================
    # CHECK RELATED / UNRELATED ISSUES
    # ========================================================

    issue_relation_results = []

    for existing_ticket in existing_ticket_data:

        relation_result = compare_issues(

            issue1=ticket_info["issue"],

            issue2=existing_ticket["issue"],

            order_id1=ticket_info["order_id"],

            order_id2=existing_ticket["order_id"]
        )

        issue_relation_results.append({

            "existing_ticket_id":
                existing_ticket["ticket_id"],

            **relation_result
        })

    duplicate_result = find_duplicate_ticket(

        new_ticket=new_ticket_data,

        existing_tickets=existing_ticket_data
    )

    # ========================================================
    # STOP DUPLICATE TICKET CREATION
    # ========================================================

    if duplicate_result["is_duplicate"]:

        return {

            "ticket_created": False,

            "duplicate": True,

            "message":
                "A similar support ticket already exists.",

            "duplicate_information":
                duplicate_result
        }

    # ========================================================
    # 4. SENTIMENT ANALYSIS
    # ========================================================

    sentiment_result = analyze_sentiment(
        request.message
    )

    # ========================================================
    # 5. DETERMINE SEVERITY
    # ========================================================

    if sentiment_result["high_risk"]:

        severity = "Critical"

    elif sentiment_result["category"] in [
        "Urgent",
        "Frustrated"
    ]:

        severity = "High"

    elif sentiment_result["sentiment"] == "NEGATIVE":

        severity = "Medium"

    else:

        severity = "Low"

    # ========================================================
    # 6. CALCULATE PRIORITY
    # ========================================================

    priority_result = calculate_priority(

        severity=severity,

        sentiment=
            sentiment_result["category"],

        waiting_minutes=0,

        customer_impact="Medium"
    )

    # ========================================================
    # 7. CALCULATE SLA
    # ========================================================

    sla_result = calculate_sla(

        priority=
            priority_result["priority"]
    )

    # ========================================================
    # 8. CHECK ESCALATION
    # ========================================================

    # New ticket has no previous unresolved conversation
    # tracked here, so use 0 minutes.

    unresolved_minutes = 0

    escalation_result = check_escalation(

        sla_result=sla_result,

        high_risk=
            sentiment_result["high_risk"],

        unresolved_minutes=unresolved_minutes
    )

    if escalation_result["escalated"]:

        escalation_result["conversation_summary"] = (
            f"Customer {request.customer_id} reported: "
            f"{request.message}. "
            f"Sentiment: {sentiment_result['category']}. "
            f"Priority: {priority_result['priority']}. "
            f"Unresolved for {unresolved_minutes} minutes."
        )

    # ========================================================
    # AFTER-HOURS QUEUE
    # ========================================================

    queue_result = determine_support_queue(

        priority=priority_result["priority"],

        high_risk=sentiment_result["high_risk"]
    )

    # ========================================================
    # 9. ROUTE TICKET
    # ========================================================

    routing_result = route_ticket(

        issue=ticket_info["issue"],

        priority=
            priority_result["priority"],

        support_queue=queue_result
    )

    # ========================================================
    # 10. GENERATE TICKET ID
    # ========================================================

    ticket_id = f"TKT-{ticket_counter:04d}"

    ticket_counter += 1

    # ========================================================
    # 11. CREATE SUPPORT TICKET
    # ========================================================

    ticket = SupportTicket(

        ticket_id=ticket_id,

        customer=
            ticket_info["customer"],

        order_id=
            ticket_info["order_id"],

        product=
            ticket_info["product"],

        issue=
            ticket_info["issue"],

        evidence=
            ticket_info.get("evidence"),

        contact_details=
            ticket_info["contact_details"],

        sentiment=
            sentiment_result["category"],

        sentiment_confidence=
            sentiment_result["confidence"],

        severity=severity,

        priority=
            priority_result["priority"],

        status="Open"
    )

    # ========================================================
    # GENERATE MASKED HANDOFF SUMMARY
    # ========================================================

    handoff_summary = generate_handoff_summary(
        ticket.model_dump()
    )

    # ========================================================
    # 12. SAVE TICKET
    # ========================================================

    tickets.append(ticket)

    # ========================================================
    # 13. RETURN COMPLETE RESULT
    # ========================================================

    return {

        "ticket_created": True,

        "ticket":
            ticket.model_dump(mode="json"),

        "routing":
            routing_result,

        "sla":
            sla_result,

        "escalation":
            escalation_result,

        "after_hours":
            queue_result,

        "duplicate":
            duplicate_result,

        "issue_relations":
            issue_relation_results,

        "handoff_summary":
            handoff_summary,

        "support_queue":
            queue_result
    }