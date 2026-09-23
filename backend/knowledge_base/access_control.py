# ==========================================
# KNOWLEDGE BASE ACCESS CONTROL
# ==========================================

ACCESS_LEVELS = {
    "PUBLIC": 1,
    "AGENT": 2,
    "ADMIN": 3,
    "RESTRICTED": 4
}


# ==========================================
# NORMALIZE ACCESS LEVEL
# ==========================================

def normalize_access_level(access_level: str) -> str:
    """
    Normalize access level to uppercase.
    """

    return access_level.strip().upper()


# ==========================================
# CHECK ACCESS
# ==========================================

def check_document_access(
    user_role: str,
    document_access_level: str
) -> dict:
    """
    Check whether a user role can access
    a knowledge-base document.
    """

    user_role = normalize_access_level(user_role)
    document_access_level = normalize_access_level(
        document_access_level
    )

    if user_role not in ACCESS_LEVELS:

        return {
            "allowed": False,
            "reason": "Unknown user role."
        }

    if document_access_level not in ACCESS_LEVELS:

        return {
            "allowed": False,
            "reason": "Unknown document access level."
        }

    user_level = ACCESS_LEVELS[user_role]
    document_level = ACCESS_LEVELS[
        document_access_level
    ]

    # Public documents can be accessed by everyone
    if document_access_level == "PUBLIC":

        return {
            "allowed": True,
            "reason": "Document is public."
        }

    # User must meet required access level
    if user_level >= document_level:

        return {
            "allowed": True,
            "reason": "User has sufficient access."
        }

    return {
        "allowed": False,
        "reason": "Insufficient access permissions."
    }


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    print("\nKnowledge Base Access Control")
    print("=============================")

    test_cases = [
        ("PUBLIC", "PUBLIC"),
        ("AGENT", "PUBLIC"),
        ("AGENT", "AGENT"),
        ("AGENT", "ADMIN"),
        ("ADMIN", "AGENT"),
        ("ADMIN", "ADMIN"),
        ("PUBLIC", "RESTRICTED")
    ]

    for user_role, document_level in test_cases:

        result = check_document_access(
            user_role,
            document_level
        )

        print(
            f"\nUser Role: {user_role}"
        )

        print(
            f"Document Level: {document_level}"
        )

        print(
            "Access Allowed:",
            result["allowed"]
        )

        print(
            "Reason:",
            result["reason"]
        )