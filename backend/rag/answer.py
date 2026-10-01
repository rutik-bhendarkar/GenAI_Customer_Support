from datetime import date
import logging

from backend.rag.retriever import (
    load_trusted_documents,
    remove_duplicate_documents,
    filter_active_documents,
    get_documents_for_date,
    filter_documents_by_access,
    search_documents,
    METADATA_FIELDS,
    MINIMUM_RELEVANCE_SCORE
)


logger = logging.getLogger(
    "genai_customer_support.rag"
)


SAFE_FALLBACK_ANSWER = (
    "I could not find enough reliable "
    "information in the knowledge base "
    "to answer this question."
)


def build_fallback_answer():
    """
    Safe customer-facing response used whenever no trusted
    knowledge-base content can answer the question.
    """

    return {
        "answer": SAFE_FALLBACK_ANSWER,
        "sources": [],
        "rag_used": False,
        "retrieval_score": 0.0,
        "chunks_retrieved": 0
    }


def contains_prompt_injection(text):
    """
    Detect common prompt-injection instructions
    inside retrieved knowledge-base content.
    """

    suspicious_patterns = [
        "ignore previous instructions",
        "ignore all previous instructions",
        "ignore the previous instructions",
        "disregard previous instructions",
        "disregard all previous instructions",
        "forget previous instructions",
        "system prompt",
        "reveal your instructions",
        "reveal confidential information",
        "bypass security",
        "override system",
        "follow these instructions instead",
        "act as system"
    ]

    text_lower = text.lower()

    for pattern in suspicious_patterns:

        if pattern in text_lower:
            return True

    return False


def generate_grounded_answer(
    query,
    user_role="PUBLIC",
    requested_date=None
):
    """
    Generate an answer using only applicable, authorized and
    security-validated knowledge-base documents.
    """

    logger.info(
        "RAG customer query: %r | user_role=%s | requested_date=%s",
        query,
        user_role,
        requested_date or "today"
    )

    # --------------------------------------------------------
    # TRUSTED DOCUMENTS ONLY
    # --------------------------------------------------------
    #
    # load_trusted_documents() applies the existing
    # knowledge-base security validation, so quarantined
    # documents (malicious_test.txt) and documents rejected by
    # prompt-injection validation can never be retrieved.

    documents = load_trusted_documents()

    # Remove duplicate policies
    documents = remove_duplicate_documents(
        documents
    )

    # --------------------------------------------------------
    # DATE HANDLING
    # --------------------------------------------------------

    if requested_date is None:

        applicable_documents = (
            filter_active_documents(
                documents,
                date.today()
            )
        )

    else:

        applicable_documents = (
            get_documents_for_date(
                documents,
                requested_date
            )
        )

    # --------------------------------------------------------
    # ACCESS CONTROL
    # --------------------------------------------------------

    authorized_documents = (
        filter_documents_by_access(
            applicable_documents,
            user_role
        )
    )

    if not authorized_documents:

        logger.info(
            "RAG no authorized knowledge-base document for role %s",
            user_role
        )

        return build_fallback_answer()

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    query_results = search_documents(
        query
    )

    # Only keep documents that are all of:
    # 1. trusted (passed knowledge-base security validation)
    # 2. applicable by date
    # 3. authorized for the user

    allowed_filenames = {
        document["filename"]
        for document in authorized_documents
    }

    filtered_results = [
        result
        for result in query_results
        if result["filename"] in allowed_filenames
    ]

    logger.info(
        "RAG retrieval scores: %s",
        [
            (result["filename"], result["score"])
            for result in filtered_results
        ]
    )

    # --------------------------------------------------------
    # INSUFFICIENT EVIDENCE
    # --------------------------------------------------------

    if not filtered_results:

        logger.info(
            "RAG no trusted document matched the query"
        )

        return build_fallback_answer()

    # Require reasonable relevance
    relevant_results = [
        result
        for result in filtered_results
        if result["score"] >= MINIMUM_RELEVANCE_SCORE
    ]

    if not relevant_results:

        logger.info(
            "RAG no document reached the relevance "
            "threshold of %.2f",
            MINIMUM_RELEVANCE_SCORE
        )

        return build_fallback_answer()

    # --------------------------------------------------------
    # PROMPT INJECTION PROTECTION (SECOND LAYER)
    # --------------------------------------------------------
    #
    # Untrusted documents are already filtered out during
    # retrieval. This check keeps the protection in place even
    # if a document were to be activated incorrectly.

    safe_results = []

    for result in relevant_results:

        if contains_prompt_injection(result["content"]):

            logger.warning(
                "RAG discarded unsafe knowledge-base document: %s",
                result["filename"]
            )

            continue

        safe_results.append(
            result
        )

    if not safe_results:

        logger.warning(
            "RAG every relevant document failed the "
            "prompt-injection check"
        )

        return build_fallback_answer()

    # --------------------------------------------------------
    # BEST EVIDENCE
    # --------------------------------------------------------

    best_result = safe_results[0]

    content = best_result["content"]
    metadata = best_result["metadata"]

    # --------------------------------------------------------
    # REMOVE METADATA FROM ANSWER
    # --------------------------------------------------------

    content_lines = content.splitlines()

    answer_lines = []

    for line in content_lines:

        if ":" in line:

            field = line.split(
                ":",
                1
            )[0].strip()

            if field in METADATA_FIELDS:
                continue

        if line.strip():

            answer_lines.append(
                line.strip()
            )

    answer = " ".join(
        answer_lines
    )

    # --------------------------------------------------------
    # SOURCE INFORMATION
    # --------------------------------------------------------

    source = {
        "filename": best_result["filename"],
        "document": metadata.get(
            "Document",
            "Unknown"
        ),
        "version": metadata.get(
            "Version",
            "Unknown"
        ),
        "product": metadata.get(
            "Product",
            "Unknown"
        ),
        "region": metadata.get(
            "Region",
            "Unknown"
        ),
        "effective_date": metadata.get(
            "Effective Date",
            "Unknown"
        ),
        "expiry_date": metadata.get(
            "Expiry Date",
            "Unknown"
        )
    }

    # --------------------------------------------------------
    # RETRIEVED CHUNKS
    # --------------------------------------------------------

    retrieved_chunks = best_result.get(
        "chunks",
        []
    )

    # --------------------------------------------------------
    # DEVELOPMENT LOGGING
    #
    # Retrieval diagnostics stay in the backend log and are
    # never returned to the customer.
    # --------------------------------------------------------

    logger.info(
        "RAG retrieved chunks: %d | best chunk score=%s | "
        "matched terms=%s",
        len(retrieved_chunks),
        (
            retrieved_chunks[0]["score"]
            if retrieved_chunks
            else 0.0
        ),
        best_result.get("matched_terms", [])
    )

    logger.info(
        "RAG final sources: %s | rag_used=True",
        [source["filename"]]
    )

    return {
        "answer": answer,
        "sources": [source],
        "rag_used": True,
        "retrieval_score": best_result["score"],
        "chunks_retrieved": len(retrieved_chunks)
    }


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("TASK 4 - GROUNDED RAG TEST")
    print("=" * 60)

    # --------------------------------------------------------
    # Test 1 - Refund
    # --------------------------------------------------------

    print("\nTest 1: Refund Policy")
    print("-" * 60)

    result = generate_grounded_answer(
        "What is the refund period?"
    )

    print(
        f"Answer: {result['answer']}"
    )

    print(
        f"Sources: {result['sources']}"
    )

    # --------------------------------------------------------
    # Test 2 - Delivery
    # --------------------------------------------------------

    print("\nTest 2: Delivery Policy")
    print("-" * 60)

    result = generate_grounded_answer(
        "How long does delivery take?"
    )

    print(
        f"Answer: {result['answer']}"
    )

    print(
        f"Sources: {result['sources']}"
    )

    # --------------------------------------------------------
    # Test 3 - Payment
    # --------------------------------------------------------

    print("\nTest 3: Duplicate Payment")
    print("-" * 60)

    result = generate_grounded_answer(
        "What should I do about a duplicate payment?"
    )

    print(
        f"Answer: {result['answer']}"
    )

    print(
        f"Sources: {result['sources']}"
    )

    # --------------------------------------------------------
    # Test 4 - Unsupported question
    # --------------------------------------------------------

    print("\nTest 4: Unsupported Question")
    print("-" * 60)

    result = generate_grounded_answer(
        "What is the weather today?"
    )

    print(
        f"Answer: {result['answer']}"
    )

    print(
        f"Sources: {result['sources']}"
    )

    # --------------------------------------------------------
    # Test 5 - Historical policy
    # --------------------------------------------------------

    print("\nTest 5: Historical Policy")
    print("-" * 60)

    historical_date = date(
        2026,
        6,
        1
    )

    result = generate_grounded_answer(
        "What is the refund period?",
        requested_date=historical_date
    )

    print(
        f"Requested Date: "
        f"{historical_date}"
    )

    print(
        f"Answer: {result['answer']}"
    )

    print(
        f"Sources: {result['sources']}"
    )