from pathlib import Path
import re
from datetime import date, datetime

from backend.knowledge_base.access_control import (
    check_document_access
)


KNOWLEDGE_BASE_PATH = Path(
    "data/knowledge_base/active"
)


# ============================================================
# METADATA EXTRACTION
# ============================================================

def extract_metadata(content):
    metadata = {}

    field_patterns = {
        "Document": r"^Document:\s*(.+)$",
        "Version": r"^Version:\s*(.+)$",
        "Product": r"^Product:\s*(.+)$",
        "Region": r"^Region:\s*(.+)$",
        "Effective Date": r"^Effective\s*Date:\s*(.+)$",
        "Expiry Date": r"^Expiry\s*Date:\s*(.+)$",
        "Access Level": r"^Access\s*Level:\s*(.+)$"
    }

    for field, pattern in field_patterns.items():

        match = re.search(
            pattern,
            content,
            re.MULTILINE | re.IGNORECASE
        )

        if match:
            metadata[field] = match.group(1).strip()

    return metadata


# ============================================================
# DATE HANDLING
# ============================================================

def parse_date(date_value):
    """
    Convert YYYY-MM-DD string into a date object.
    """

    try:
        return datetime.strptime(
            date_value,
            "%Y-%m-%d"
        ).date()

    except (ValueError, TypeError):
        return None


def is_policy_active(metadata, check_date=None):
    """
    Check whether a policy is active on a given date.

    A policy is active when:
        Effective Date <= check_date <= Expiry Date
    """

    if check_date is None:
        check_date = date.today()

    effective_date = parse_date(
        metadata.get("Effective Date")
    )

    expiry_date = parse_date(
        metadata.get("Expiry Date")
    )

    # Missing or invalid effective date
    # means the policy cannot be trusted.
    if effective_date is None:
        return False

    # Policy is not active yet.
    if check_date < effective_date:
        return False

    # Policy has expired.
    if expiry_date is not None:
        if check_date > expiry_date:
            return False

    return True


# ============================================================
# LOAD DOCUMENTS
# ============================================================

def load_documents():
    """
    Load all TXT documents from the active knowledge base.
    """

    documents = []

    if not KNOWLEDGE_BASE_PATH.exists():
        return documents

    for file_path in sorted(
        KNOWLEDGE_BASE_PATH.glob("*.txt")
    ):

        try:

            content = file_path.read_text(
                encoding="utf-8"
            )

            metadata = extract_metadata(
                content
            )

            documents.append(
                {
                    "filename": file_path.name,
                    "content": content,
                    "metadata": metadata
                }
            )

        except Exception as error:

            print(
                f"Failed to read "
                f"{file_path.name}: {error}"
            )

    return documents


# ============================================================
# DUPLICATE DOCUMENT REMOVAL
# ============================================================

def remove_duplicate_documents(documents):
    """
    Remove duplicate policy versions.

    Two documents are considered duplicates when their
    important policy metadata is identical.
    """

    unique_documents = {}

    for document in documents:

        metadata = document.get(
            "metadata",
            {}
        )

        key = (
            metadata.get("Document"),
            metadata.get("Version"),
            metadata.get("Product"),
            metadata.get("Region"),
            metadata.get("Effective Date"),
            metadata.get("Expiry Date"),
            metadata.get("Access Level")
        )

        if key not in unique_documents:

            unique_documents[key] = document

    return list(
        unique_documents.values()
    )


# ============================================================
# DATE FILTERING
# ============================================================

def filter_active_documents(
    documents,
    check_date=None
):
    """
    Return only policies active on the requested date.
    """

    active_documents = []

    for document in documents:

        if is_policy_active(
            document.get("metadata", {}),
            check_date
        ):

            active_documents.append(
                document
            )

    active_documents = remove_duplicate_documents(
        active_documents
    )

    return select_latest_policy_versions(
        active_documents
    )


def get_documents_for_date(
    documents,
    requested_date
):
    """
    Return policies applicable on a historical date.
    """

    matching_documents = []

    for document in documents:

        if is_policy_active(
            document.get("metadata", {}),
            requested_date
        ):

            matching_documents.append(
                document
            )

    matching_documents = remove_duplicate_documents(
        matching_documents
    )

    return select_latest_policy_versions(
        matching_documents
    )

def select_latest_policy_versions(documents):
    """
    Select the latest applicable version for each policy.

    Policies are grouped by:
    Document + Product + Region

    The highest numeric version is selected.
    """

    latest_policies = {}

    for document in documents:

        metadata = document.get("metadata", {})

        document_name = metadata.get(
            "Document",
            ""
        )

        product = metadata.get(
            "Product",
            ""
        )

        region = metadata.get(
            "Region",
            ""
        )

        key = (
            document_name,
            product,
            region
        )

        version_text = metadata.get(
            "Version",
            "0"
        )

        try:
            version_number = float(
                version_text
            )
        except (ValueError, TypeError):
            version_number = 0

        if key not in latest_policies:

            latest_policies[key] = (
                version_number,
                document
            )

        else:

            current_version = (
                latest_policies[key][0]
            )

            if version_number > current_version:

                latest_policies[key] = (
                    version_number,
                    document
                )

    return [
        document
        for _, document in latest_policies.values()
    ]
# ============================================================
# ACCESS CONTROL
# ============================================================

def filter_documents_by_access(
    documents,
    user_role
):
    """
    Return only documents the user is authorized to access.
    """

    authorized_documents = []

    for document in documents:

        metadata = document.get(
            "metadata",
            {}
        )

        document_level = metadata.get(
            "Access Level",
            "PUBLIC"
        ).upper()

        access_result = check_document_access(
            user_role,
            document_level
        )

        if access_result.get("allowed", False):

            authorized_documents.append(
                document
            )

    return authorized_documents


# ============================================================
# DOCUMENT SEARCH
# ============================================================

def search_documents(query):
    """
    Improved keyword-based document retrieval.

    Gives higher weight to:
    - exact query phrases
    - matching important words
    - matching multiple query terms
    """

    documents = load_documents()

    documents = remove_duplicate_documents(
        documents
    )

    query_lower = query.lower().strip()

    query_words = [
        word.lower()
        for word in re.findall(
            r"\b\w+\b",
            query_lower
        )
        if len(word) > 2
    ]

    results = []

    for document in documents:

        content = document["content"]
        searchable_text = content.lower()

        score = 0

        # ----------------------------------------------------
        # Exact phrase matching
        # ----------------------------------------------------

        if query_lower in searchable_text:
            score += 5

        # ----------------------------------------------------
        # Individual keyword matching
        # ----------------------------------------------------

        matched_words = []

        for word in query_words:

            if word in searchable_text:

                matched_words.append(word)

                # Important domain words receive higher weight
                if word in {
                    "refund",
                    "payment",
                    "delivery",
                    "order",
                    "security",
                    "password",
                    "otp",
                    "duplicate",
                    "charged",
                    "transaction",
                    "troubleshooting",
                    "product"
                }:
                    score += 2

                else:
                    score += 1

        # ----------------------------------------------------
        # Normalize score
        # ----------------------------------------------------

        if not matched_words:
            continue

        normalized_score = score / max(
            len(query_words) * 2,
            1
        )

        results.append(
            {
                "filename": document["filename"],
                "score": round(
                    normalized_score,
                    3
                ),
                "metadata": document["metadata"],
                "content": content
            }
        )

    results.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return results


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":

    print("=" * 50)
    print("RAG RETRIEVER TEST")
    print("=" * 50)

    # --------------------------------------------------------
    # Load documents
    # --------------------------------------------------------

    documents = load_documents()

    print(
        f"\nDocuments loaded: "
        f"{len(documents)}"
    )

    for document in documents:

        print(
            f"- {document['filename']} | "
            f"Version: "
            f"{document['metadata'].get('Version', 'Unknown')}"
        )

    # --------------------------------------------------------
    # Duplicate removal test
    # --------------------------------------------------------

    unique_documents = (
        remove_duplicate_documents(
            documents
        )
    )

    print("\nUnique Documents")
    print("-" * 50)

    print(
        f"Unique documents: "
        f"{len(unique_documents)}"
    )

    # --------------------------------------------------------
    # Search test
    # --------------------------------------------------------

    print("\nSearch Test")
    print("-" * 50)

    query = "refund order"

    results = search_documents(
        query
    )

    print(
        f"Query: {query}"
    )

    print(
        f"Results found: "
        f"{len(results)}"
    )

    for result in results:

        print(
            f"\nSource: "
            f"{result['filename']}"
        )

        print(
            f"Score: "
            f"{result['score']}"
        )

        print(
            f"Metadata: "
            f"{result['metadata']}"
        )

    # --------------------------------------------------------
    # Current policy date test
    # --------------------------------------------------------

    print("\n" + "=" * 50)
    print("RAG POLICY DATE FILTER TEST")
    print("=" * 50)

    test_date = date(
        2026,
        9,
        21
    )

    active_documents = (
        filter_active_documents(
            unique_documents,
            test_date
        )
    )

    print(
        f"Test Date: "
        f"{test_date}"
    )

    print(
        f"Total Unique Documents: "
        f"{len(unique_documents)}"
    )

    print(
        f"Active Documents: "
        f"{len(active_documents)}"
    )

    for document in active_documents:

        print(
            f"- {document['filename']} | "
            f"Effective: "
            f"{document['metadata'].get('Effective Date')} | "
            f"Expiry: "
            f"{document['metadata'].get('Expiry Date')}"
        )

    # --------------------------------------------------------
    # Historical policy test
    # --------------------------------------------------------

    print("\nHistorical Policy Test")
    print("-" * 50)

    historical_date = date(
        2026,
        6,
        1
    )

    historical_documents = (
        get_documents_for_date(
            unique_documents,
            historical_date
        )
    )

    print(
        f"Requested Historical Date: "
        f"{historical_date}"
    )

    print(
        f"Documents Found: "
        f"{len(historical_documents)}"
    )

    for document in historical_documents:

        print(
            f"- {document['filename']} | "
            f"Effective: "
            f"{document['metadata'].get('Effective Date')} | "
            f"Expiry: "
            f"{document['metadata'].get('Expiry Date')}"
        )

    # --------------------------------------------------------
    # Access control test
    # --------------------------------------------------------

    print("\nAccess Control Test")
    print("-" * 50)

    public_documents = (
        filter_documents_by_access(
            unique_documents,
            "PUBLIC"
        )
    )

    agent_documents = (
        filter_documents_by_access(
            unique_documents,
            "AGENT"
        )
    )

    admin_documents = (
        filter_documents_by_access(
            unique_documents,
            "ADMIN"
        )
    )

    print(
        f"PUBLIC user can access: "
        f"{len(public_documents)} documents"
    )

    print(
        f"AGENT user can access: "
        f"{len(agent_documents)} documents"
    )

    print(
        f"ADMIN user can access: "
        f"{len(admin_documents)} documents"
    )