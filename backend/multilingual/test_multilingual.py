from backend.multilingual.language import (
    detect_language,
    requires_language_clarification
)

from backend.multilingual.normalization import normalize_message
from backend.multilingual.context import ConversationContext
from backend.multilingual.session import SessionManager


# ============================================================
# BASIC MESSAGE PROCESSING
# ============================================================

def process_message(
    session_manager,
    context_manager,
    customer_id,
    message
):
    # 1. Detect language
    language = detect_language(message)

    # 2. Normalize while preserving important entities
    normalized = normalize_message(message)

    # 3. Store conversation context
    context_manager.add_message(
        "customer",
        message
    )

    # 4. Update session activity
    session_manager.update_activity(
        customer_id
    )

    return {
        "language": language,
        "normalized_message": normalized,
        "history": context_manager.get_history(),
        "session_status": session_manager.check_session_status(
            customer_id
        )
    }


# ============================================================
# COMPLETE MULTILINGUAL PIPELINE
# ============================================================

def multilingual_pipeline(
    session_manager,
    context_manager,
    customer_id,
    message
):
    # 1. Detect language
    language = detect_language(message)

    # 2. Check language confidence
    clarification = requires_language_clarification(
        language
    )

    # 3. Normalize message
    normalized = normalize_message(message)

    # 4. Store original message in context
    context_manager.add_message(
        "customer",
        message
    )

    # 5. Update session activity
    session_manager.update_activity(
        customer_id
    )

    # 6. Check session status
    session_status = session_manager.check_session_status(
        customer_id
    )

    return {
        "message": message,
        "language": language,
        "clarification_required": clarification,
        "normalized": normalized,
        "context_count": context_manager.get_message_count(),
        "session": session_status
    }


# ============================================================
# MAIN TEST
# ============================================================

def main():

    customer_id = "CUST001"

    # Create session manager
    session_manager = SessionManager()

    # Keep maximum 10 messages in conversation context
    context_manager = ConversationContext(
        max_messages=10
    )

    # Create customer session
    session_manager.create_session(
        customer_id
    )

    # ========================================================
    # TEST 1: LANGUAGE SWITCHING
    # ========================================================

    print("=" * 60)
    print("MULTILINGUAL CONVERSATION TEST")
    print("=" * 60)

    messages = [
        "My order ORDER-12345 is delayed.",
        "मेरा ऑर्डर ORD12345 अभी तक नहीं आया है।",
        "माझा ऑर्डर ORD12345 अजून आलेला नाही.",
        "Can you please check my order?"
    ]

    for message in messages:

        result = process_message(
            session_manager,
            context_manager,
            customer_id,
            message
        )

        print("\nMessage:", message)
        print(
            "Language:",
            result["language"]
        )
        print(
            "Normalized:",
            result["normalized_message"]
        )
        print(
            "Session:",
            result["session_status"]["status"]
        )
        print(
            "Context messages:",
            len(result["history"])
        )

    # ========================================================
    # TEST 2: CONVERSATION CONTEXT
    # ========================================================

    print("\n" + "=" * 60)
    print("FINAL CONVERSATION CONTEXT")
    print("=" * 60)

    for msg in context_manager.get_history():
        print(msg)

    # ========================================================
    # TEST 3: 10 MESSAGE CONTEXT
    # ========================================================

    print("\n" + "=" * 60)
    print("10 MESSAGE CONTEXT TEST")
    print("=" * 60)

    for i in range(4, 16):

        process_message(
            session_manager,
            context_manager,
            customer_id,
            f"Message number {i}"
        )

    history = context_manager.get_history()

    print(
        "Total messages stored:",
        len(history)
    )

    print("\nStored Messages:")

    for msg in history:
        print(msg)

    # ========================================================
    # TEST 4: MIXED LANGUAGE
    # ========================================================

    print("\n" + "=" * 60)
    print("MIXED LANGUAGE TEST")
    print("=" * 60)

    mixed_messages = [
        "My order ORD12345 अभी तक नहीं आया है",
        "माझा payment failed आहे, please help",
        "Can you check माझा order?"
    ]

    for message in mixed_messages:

        result = process_message(
            session_manager,
            context_manager,
            customer_id,
            message
        )

        print("\nMixed Message:", message)
        print(
            "Language:",
            result["language"]
        )
        print(
            "Normalized:",
            result["normalized_message"]
        )
        print(
            "Session:",
            result["session_status"]["status"]
        )

    # ========================================================
    # TEST 5: FINAL MULTILINGUAL PIPELINE
    # ========================================================

    print("\n" + "=" * 60)
    print("FINAL MULTILINGUAL PIPELINE TEST")
    print("=" * 60)

    pipeline_messages = [
        "My order ORDER-12345 is delayed.",
        "मेरा ऑर्डर ORD12345 अभी तक नहीं आया है।",
        "माझा ऑर्डर ORD12345 अजून आलेला नाही.",
        "Can you check it please?"
    ]

    for message in pipeline_messages:

        result = multilingual_pipeline(
            session_manager,
            context_manager,
            customer_id,
            message
        )

        print("\nMessage:")
        print(result["message"])

        print(
            "Language:",
            result["language"]
        )

        print(
            "Clarification required:",
            result["clarification_required"]
        )

        print(
            "Normalized:",
            result["normalized"]
        )

        print(
            "Context count:",
            result["context_count"]
        )

        print(
            "Session:",
            result["session"]["status"]
        )


# ============================================================
# PROGRAM ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()