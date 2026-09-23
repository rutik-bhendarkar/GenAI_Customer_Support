from datetime import date

from backend.rag.retriever import (
    load_documents,
    remove_duplicate_documents,
    filter_active_documents,
    get_documents_for_date,
    filter_documents_by_access,
    search_documents
)
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
    Generate an answer using only applicable
    and authorized knowledge-base documents.
    """

    documents = load_documents()

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

        return {
            "answer": (
                "I could not find an authorized "
                "knowledge-base document that can "
                "answer this question."
            ),
            "sources": []
        }

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    query_results = search_documents(
        query
    )

    # Only keep documents that are both:
    # 1. applicable by date
    # 2. authorized for the user

    allowed_filenames = {
        document["filename"]
        for document in authorized_documents
    }

    filtered_results = [
        result
        for result in query_results
        if result["filename"] in allowed_filenames
    ]

    # --------------------------------------------------------
    # INSUFFICIENT EVIDENCE
    # --------------------------------------------------------

    if not filtered_results:

        return {
            "answer": (
                "I could not find enough reliable "
                "information in the knowledge base "
                "to answer this question."
            ),
            "sources": []
        }

    # Require reasonable relevance
    relevant_results = [
        result
        for result in filtered_results
        if result["score"] >= 0.20
    ]

    if not relevant_results:

        return {
            "answer": (
                "I could not find enough reliable "
                "information in the knowledge base "
                "to answer this question."
            ),
            "sources": []
        }

    # --------------------------------------------------------
    # BEST EVIDENCE
    # --------------------------------------------------------

    best_result = relevant_results[0]

    content = best_result["content"]
    metadata = best_result["metadata"]

# --------------------------------------------------------
# PROMPT INJECTION PROTECTION
# --------------------------------------------------------

    if contains_prompt_injection(content):

        return {
            "answer": (
                "The retrieved knowledge-base document "
                "contains unsafe or suspicious instructions. "
                "I cannot use that document to answer this question."
            ),
            "sources": []
        }

    # --------------------------------------------------------
    # REMOVE METADATA FROM ANSWER
    # --------------------------------------------------------

    content_lines = content.splitlines()

    answer_lines = []

    metadata_fields = {
        "Document",
        "Version",
        "Product",
        "Region",
        "Effective Date",
        "Expiry Date",
        "Access Level"
    }

    for line in content_lines:

        if ":" in line:

            field = line.split(
                ":",
                1
            )[0].strip()

            if field in metadata_fields:
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

    return {
        "answer": answer,
        "sources": [source]
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