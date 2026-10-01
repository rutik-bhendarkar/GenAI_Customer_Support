from pathlib import Path
import logging
import re
from datetime import date, datetime

from backend.knowledge_base.access_control import (
    check_document_access
)

# Reuse the existing knowledge-base security validation so that
# untrusted documents (missing metadata, too short, or containing
# prompt-injection instructions) are never retrievable.
from backend.knowledge_base.validator import (
    quality_check
)


logger = logging.getLogger(
    "genai_customer_support.rag"
)


KNOWLEDGE_BASE_PATH = Path(
    "data/knowledge_base/active"
)


# ============================================================
# DOCUMENT METADATA FIELDS
# ============================================================

METADATA_FIELDS = {
    "Document",
    "Version",
    "Product",
    "Region",
    "Effective Date",
    "Expiry Date",
    "Access Level"
}


# ============================================================
# RETRIEVAL TUNING
# ============================================================

# A trusted document must reach this relevance score before its
# content may be used to answer a customer question.
MINIMUM_RELEVANCE_SCORE = 0.20

# How much weight question coverage carries versus matched
# domain vocabulary strength.
COVERAGE_WEIGHT = 0.6
KEYWORD_WEIGHT = 0.4

# Matched vocabulary is capped so a single repeated topic cannot
# dominate the score.
MAX_KEYWORD_WEIGHT = 4


# ============================================================
# METADATA EXTRACTION
# ============================================================

def extract_metadata(content):
    metadata = {}

    field_patterns = {
        field: rf"^{re.escape(field)}:\s*(.+)$"
        for field in METADATA_FIELDS
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

    Every document is evaluated with the existing knowledge-base
    security/quality validation. Documents that fail validation
    (missing metadata, empty/too short content, or prompt
    injection) are marked as untrusted and are never used for
    retrieval.
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

            validation = quality_check(
                file_path
            )

            documents.append(
                {
                    "filename": file_path.name,
                    "content": content,
                    "metadata": metadata,
                    "trusted": bool(
                        validation.get("passed", False)
                    ),
                    "validation_issues": validation.get(
                        "issues",
                        []
                    )
                }
            )

        except Exception as error:

            print(
                f"Failed to read "
                f"{file_path.name}: {error}"
            )

    return documents


def load_trusted_documents():
    """
    Return only knowledge-base documents that passed the existing
    security validation.

    Quarantined documents (for example malicious_test.txt) are not
    part of the active folder and documents rejected by
    prompt-injection validation are excluded here.
    """

    trusted_documents = []

    rejected_documents = []

    for document in load_documents():

        if document.get("trusted"):

            trusted_documents.append(document)

        else:

            rejected_documents.append(
                {
                    "filename": document["filename"],
                    "issues": document.get(
                        "validation_issues",
                        []
                    )
                }
            )

    if rejected_documents:

        logger.warning(
            "Knowledge-base documents excluded by security "
            "validation: %s",
            rejected_documents
        )

    logger.info(
        "Trusted knowledge-base documents: %s",
        [
            document["filename"]
            for document in trusted_documents
        ]
    )

    return trusted_documents


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
# RETRIEVAL VOCABULARY
# ============================================================

# Words that carry no retrieval signal in a support message.
STOPWORDS = {
    "the", "and", "for", "are", "but", "not", "you", "your", "yours",
    "all", "any", "can", "could", "would", "should", "will", "have",
    "has", "had", "was", "were", "been", "being", "this", "that",
    "these", "those", "with", "without", "from", "into", "about",
    "there", "here", "what", "when", "where", "which", "who", "why",
    "how", "our", "out", "get", "got", "give", "gave", "need", "want",
    "wants", "please", "help", "tell", "some", "something", "anything",
    "nothing", "still", "very", "just", "also", "them", "they", "she",
    "him", "her", "his", "its", "did", "does", "doing", "done", "am",
    "is", "my", "me", "i", "we", "us", "it", "a", "an", "of", "in",
    "on", "at", "to", "as", "by", "or", "if", "so", "do", "be", "new",
    "now", "today", "recently", "already", "again", "more", "most",
    "much", "many", "same", "other", "another", "because", "since"
}


# Domain vocabulary that maps customer wording onto the topics
# covered by the trusted knowledge base.
DOMAIN_CONCEPTS = {

    "delivery": [
        "delivery", "deliver", "delivered", "deliveries", "shipment",
        "shipping", "shipped", "dispatch", "dispatched", "courier",
        "parcel", "package", "arrive", "arrived", "arrival", "transit",
        "tracking", "track"
    ],

    "refund": [
        "refund", "refunds", "refunded", "reimburse", "reimbursement",
        "money back", "return", "returns", "returned", "cancel",
        "cancelled", "canceled", "cancellation"
    ],

    "payment": [
        "payment", "payments", "pay", "paid", "paying", "charge",
        "charged", "charges", "billing", "billed", "transaction",
        "transactions", "invoice", "failed", "failure", "declined",
        "decline", "deducted", "duplicate", "twice", "overcharged"
    ],

    "troubleshooting": [
        "technical", "technically", "troubleshooting", "troubleshoot",
        "problem", "issue", "error", "broken", "malfunction",
        "malfunctioning", "fault", "faulty", "device", "connectivity",
        "network", "not working", "working", "switch on", "turn on",
        "restart"
    ],

    "order": [
        "order", "orders", "purchase", "purchased", "item", "items",
        "product", "products"
    ],

    "security": [
        "security", "unauthorized", "fraud", "fraudulent", "suspicious",
        "hacked", "safe", "safety", "breach"
    ],

    "credentials": [
        "password", "passwords", "otp", "credential", "credentials",
        "login", "pin"
    ]
}


# ============================================================
# QUERY TERM PROCESSING
# ============================================================

def stem_token(token):
    """
    Apply very light suffix stripping so simple plural and verb
    forms map onto one base token.
    """

    for suffix in ("ing", "ed", "es", "s"):

        if (
            token.endswith(suffix)
            and len(token) - len(suffix) >= 3
        ):

            return token[: -len(suffix)]

    return token


def build_term_concept_map():
    """
    Map every vocabulary word (and its base form) onto the
    domain concepts it belongs to.
    """

    mapping = {}

    for concept, variants in DOMAIN_CONCEPTS.items():

        for variant in variants:

            for form in (variant, stem_token(variant)):

                mapping.setdefault(
                    form,
                    set()
                ).add(concept)

    return mapping


TERM_CONCEPTS = build_term_concept_map()


def resolve_concepts(token):
    """
    Return the domain concepts a query token belongs to.
    """

    concepts = TERM_CONCEPTS.get(token)

    if concepts:

        return concepts

    return TERM_CONCEPTS.get(
        stem_token(token),
        set()
    )


def extract_query_terms(query):
    """
    Convert a customer question into retrieval terms.

    Stopwords and structural identifiers (order IDs, amounts and
    dates) are removed because they do not describe the
    knowledge-base topic and only dilute relevance.
    """

    terms = []

    seen = set()

    for raw_token in re.findall(r"[A-Za-z0-9]+", query):

        token = raw_token.lower()

        if any(character.isdigit() for character in raw_token):
            continue

        if len(token) <= 2:
            continue

        if token in STOPWORDS:
            continue

        if token in seen:
            continue

        seen.add(token)

        terms.append(
            {
                "token": token,
                "concepts": resolve_concepts(token)
            }
        )

    return terms



# ============================================================
# TERM MATCHING
# ============================================================

TERM_PATTERN_CACHE = {}


def build_term_pattern(term_text):
    """
    Build (and cache) a word-prefix pattern so "deliver" also
    matches "delivered" and "delivery".
    """

    pattern = TERM_PATTERN_CACHE.get(term_text)

    if pattern is None:

        pattern = re.compile(
            r"\b" + re.escape(term_text),
            re.IGNORECASE
        )

        TERM_PATTERN_CACHE[term_text] = pattern

    return pattern


def term_matches_text(term, text):
    """
    Check whether a query term (or one of its domain vocabulary
    variants) appears in the given text.
    """

    if term["concepts"]:

        variants = [
            variant
            for concept in term["concepts"]
            for variant in DOMAIN_CONCEPTS[concept]
        ]

    else:

        variants = [term["token"]]

    for variant in variants:

        if build_term_pattern(variant).search(text):

            return True

    return False


def collect_matched_terms(query_terms, text):
    """
    Return the query terms that are present in the given text.
    """

    return [
        term
        for term in query_terms
        if term_matches_text(term, text)
    ]


def calculate_relevance_score(matched_terms, total_terms):
    """
    Combine how much of the question a document covers with the
    strength of the matched domain vocabulary.

    Score range: 0.0 (no evidence) to 1.0 (full coverage).
    """

    if not matched_terms or total_terms <= 0:

        return 0.0

    coverage = len(matched_terms) / total_terms

    matched_weight = sum(
        2 if term["concepts"] else 1
        for term in matched_terms
    )

    keyword_strength = min(
        matched_weight,
        MAX_KEYWORD_WEIGHT
    ) / MAX_KEYWORD_WEIGHT

    score = (
        COVERAGE_WEIGHT * coverage
        + KEYWORD_WEIGHT * keyword_strength
    )

    return round(
        min(score, 1.0),
        3
    )


# ============================================================
# DOCUMENT CHUNKING
# ============================================================

def is_metadata_line(line):
    """
    Detect a metadata header line so it is not treated as
    customer-facing policy content.
    """

    if ":" not in line:

        return False

    field = line.split(
        ":",
        1
    )[0].strip()

    return field in METADATA_FIELDS


def split_into_chunks(content):
    """
    Split a knowledge-base document into paragraph chunks with
    the metadata header removed.
    """

    chunks = []

    buffer = []

    for line in content.splitlines():

        stripped = line.strip()

        if is_metadata_line(stripped):
            continue

        if not stripped:

            if buffer:

                chunks.append(
                    " ".join(buffer)
                )

                buffer = []

            continue

        buffer.append(stripped)

    if buffer:

        chunks.append(
            " ".join(buffer)
        )

    return chunks


def document_body(content):
    """
    Return the searchable policy body of a document with the
    metadata header removed.
    """

    return " ".join(
        split_into_chunks(content)
    )


def collect_relevant_chunks(content, query_terms):
    """
    Find the document chunks that actually match the customer
    question, most relevant chunk first.
    """

    chunks = []

    for index, chunk in enumerate(
        split_into_chunks(content)
    ):

        matched_terms = collect_matched_terms(
            query_terms,
            chunk
        )

        if not matched_terms:
            continue

        chunks.append(
            {
                "index": index,
                "text": chunk,
                "score": calculate_relevance_score(
                    matched_terms,
                    len(query_terms)
                ),
                "matched_terms": [
                    term["token"]
                    for term in matched_terms
                ]
            }
        )

    chunks.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return chunks


# ============================================================
# DOCUMENT SEARCH
# ============================================================

def search_documents(query):
    """
    Keyword-based retrieval over the trusted knowledge base.

    Documents are ranked by question coverage, with domain
    vocabulary carrying more weight than generic words. Only
    documents that passed the knowledge-base security validation
    are searched.
    """

    documents = load_trusted_documents()

    documents = remove_duplicate_documents(
        documents
    )

    query_terms = extract_query_terms(query)

    results = []

    for document in documents:

        content = document["content"]

        # Policy text is matched on the document body, not on
        # the metadata header.
        body = document_body(
            content
        )

        matched_terms = collect_matched_terms(
            query_terms,
            body
        )

        if not matched_terms:
            continue

        # A single generic word is not enough evidence.
        if (
            not any(
                term["concepts"]
                for term in matched_terms
            )
            and len(matched_terms) < 2
        ):
            continue

        chunks = collect_relevant_chunks(
            content,
            query_terms
        )

        results.append(
            {
                "filename": document["filename"],
                "score": calculate_relevance_score(
                    matched_terms,
                    len(query_terms)
                ),
                "matched_terms": [
                    term["token"]
                    for term in matched_terms
                ],
                "chunks": chunks,
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
