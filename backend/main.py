from datetime import date
import logging
from pathlib import Path
from shutil import copyfileobj

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator


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
# TASK 5 - MULTIMODAL
# ============================================================

from backend.multimodal.file_handler import (
    create_upload_directories,
    is_allowed_file
)

from backend.multimodal.processor import process_file


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
# LOGGING
# ============================================================

# Detailed diagnostics (for example OCR/upload failures)
# are logged on the backend only. API responses never
# contain stack traces.

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger("genai_customer_support")


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="GenAI Customer Support",
    description="AI-powered customer support chatbot",
    version="1.0.0"
)

# ============================================================
# CORS - FRONTEND CONNECTION
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# GLOBAL ERROR HANDLING
# ============================================================

@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    """
    Return a clean JSON error for unexpected backend failures.

    The full diagnostic (including the traceback) is written to the
    backend log only. The customer-facing response never contains a
    stack trace or internal details.
    """

    logger.exception(
        "Unhandled error while processing %s %s",
        request.method,
        request.url.path
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": (
                "An unexpected error occurred while processing "
                "your request. Please try again."
            )
        }
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

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        """
        Reject empty or whitespace-only messages.

        Without this guard an empty message would travel through the
        whole pipeline and produce a meaningless analysis. The
        customer instead receives a clear validation error (HTTP 422).
        """

        stripped = value.strip()

        if not stripped:

            raise ValueError(
                "Message must not be empty. "
                "Please describe your issue."
            )

        return stripped


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
# TASK 5 - MULTIMODAL FILE UPLOAD
# ============================================================

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    customer_message: str = Form("")
):
    """
    Upload and process a customer document/image.

    Supported formats:
    - PDF
    - PNG
    - JPG
    - JPEG
    """

    # --------------------------------------------------------
    # STEP 1 - CREATE REQUIRED DIRECTORIES
    # --------------------------------------------------------

    create_upload_directories()

    # --------------------------------------------------------
    # STEP 2 - VALIDATE FILE NAME
    # --------------------------------------------------------

    if not file.filename:

        return {
            "success": False,
            "stage": "file_validation",
            "message": "No filename was provided."
        }

    # Prevent path traversal by keeping only the filename.
    safe_filename = Path(file.filename).name

    # --------------------------------------------------------
    # STEP 3 - VALIDATE FILE EXTENSION
    # --------------------------------------------------------

    if not is_allowed_file(safe_filename):

        return {
            "success": False,
            "stage": "file_validation",
            "filename": safe_filename,
            "message": "Unsupported file type."
        }

    # --------------------------------------------------------
    # STEP 4 - SAVE TO INCOMING DIRECTORY
    # --------------------------------------------------------

    incoming_path = (
        Path("data")
        / "uploads"
        / "incoming"
        / safe_filename
    )

    try:

        with incoming_path.open("wb") as buffer:

            copyfileobj(
                file.file,
                buffer
            )

    except Exception as error:

        return {
            "success": False,
            "stage": "file_upload",
            "filename": safe_filename,
            "message": "Failed to save uploaded file.",
            "error": str(error)
        }

    # --------------------------------------------------------
    # STEP 5 - PROCESS MULTIMODAL FILE
    # --------------------------------------------------------

    try:

        result = process_file(
            incoming_path,
            customer_message=customer_message or None
        )

        if result.get("success"):

            logger.info(
                "Multimodal upload processed successfully: %s",
                safe_filename
            )

        else:

            logger.warning(
                "Multimodal upload failed for %s at stage '%s': %s",
                safe_filename,
                result.get("stage"),
                result.get("error") or result.get("message")
            )

        return result

    except Exception as error:

        # Full diagnostics stay in the backend log.
        logger.exception(
            "Unexpected error while processing uploaded file %s",
            safe_filename
        )

        return {
            "success": False,
            "stage": "multimodal_processing",
            "filename": safe_filename,
            "message": "An unexpected error occurred while processing the file.",
            "error": str(error),
            "error_type": type(error).__name__
        }


# ============================================================
# CHAT API
# ============================================================

@app.post("/chat")
def chat(request: ChatRequest):

    # ========================================================
    # TASK 6 - MULTILINGUAL PROCESSING
    # ========================================================

    # --------------------------------------------------------
    # Get/create customer session
    # --------------------------------------------------------

    if request.customer_id not in session_manager.sessions:

        session_manager.create_session(
            request.customer_id
        )

    # --------------------------------------------------------
    # Get isolated conversation context
    # --------------------------------------------------------

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
    # 6. Generate conversation summary
    # --------------------------------------------------------

    recent_messages = context_manager.get_recent_messages(
        5
    )

    summary_parts = []

    for message in recent_messages:

        if message["role"] == "customer":

            summary_parts.append(
                message["content"]
            )

    conversation_summary = " | ".join(
        summary_parts
    )

    session_manager.set_summary(
        request.customer_id,
        conversation_summary
    )

    # --------------------------------------------------------
    # 7. Get session status
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

    unresolved_minutes = (
        session_manager.get_unresolved_minutes(
            request.customer_id
        )
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

            f"Sentiment: "
            f"{sentiment_result['category']}. "

            f"Priority: "
            f"{priority_result['priority']}. "

            f"Unresolved for "
            f"{unresolved_minutes} minutes."
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
    # TASK 4 - RAG DEVELOPMENT LOGGING
    #
    # Retrieval diagnostics are written to the backend log only
    # and are never exposed in the customer-facing response.
    # ========================================================

    logger.info(
        "RAG /chat | customer_query=%r | rag_used=%s | "
        "retrieval_score=%s | chunks_retrieved=%s | sources=%s",
        request.message,
        rag_result.get("rag_used", False),
        rag_result.get("retrieval_score", 0.0),
        rag_result.get("chunks_retrieved", 0),
        [
            source.get("filename")
            for source in rag_result.get("sources", [])
        ]
    )

    # ========================================================
    # RETURN CHATBOT RESULT
    # ========================================================

    return {

        # ----------------------------------------------------
        # Original message
        # ----------------------------------------------------

        "message":
            request.message,

        # ====================================================
        # TASK 6 - MULTILINGUAL
        # ====================================================

        "language":
            language_result,

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
            rag_result.get(
                "rag_used",
                len(rag_result["sources"]) > 0
            )
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

            "ticket_created":
                False,

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

            "ticket_created":
                False,

            "duplicate":
                True,

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

        unresolved_minutes=
            unresolved_minutes
    )

    # ========================================================
    # ADD ESCALATION CONVERSATION SUMMARY
    # ========================================================

    if escalation_result["escalated"]:

        escalation_result["conversation_summary"] = (

            f"Customer {request.customer_id} reported: "

            f"{request.message}. "

            f"Sentiment: "
            f"{sentiment_result['category']}. "

            f"Priority: "
            f"{priority_result['priority']}. "

            f"Unresolved for "
            f"{unresolved_minutes} minutes."
        )

    # ========================================================
    # AFTER-HOURS QUEUE
    # ========================================================

    queue_result = determine_support_queue(

        priority=
            priority_result["priority"],

        high_risk=
            sentiment_result["high_risk"]
    )

    # ========================================================
    # 9. ROUTE TICKET
    # ========================================================

    routing_result = route_ticket(

        issue=
            ticket_info["issue"],

        priority=
            priority_result["priority"],

        support_queue=
            queue_result
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

        ticket_id=
            ticket_id,

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

        severity=
            severity,

        priority=
            priority_result["priority"],

        status=
            "Open"
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

    tickets.append(
        ticket
    )

    # ========================================================
    # 13. RETURN COMPLETE RESULT
    # ========================================================

    return {

        "ticket_created":
            True,

        "ticket":
            ticket.model_dump(
                mode="json"
            ),

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