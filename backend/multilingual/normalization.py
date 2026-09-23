import re


# ============================================================
# PROTECTED INFORMATION PATTERNS
# ============================================================

ORDER_ID_PATTERN = r"\b(?:ORD(?:ER)?[- ]?\d{3,})\b"

ERROR_CODE_PATTERN = (
    r"\b(?:ERR[- ]?\d{3,5}|ERROR[- ]?\d{3,5}|E\d{3,5})\b"
)

DATE_PATTERN = (
    r"\b(?:\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4})\b"
)

PRODUCT_CODE_PATTERN = (
    r"\b[A-Z]{1,5}[-_][A-Z0-9]{2,15}\b"
)


# ============================================================
# EXTRACT PROTECTED ENTITIES
# ============================================================

def extract_protected_entities(text):
    """
    Extract information that must remain unchanged
    during multilingual processing.
    """

    if not text:
        return {
            "order_ids": [],
            "error_codes": [],
            "dates": [],
            "product_codes": []
        }

    return {
        "order_ids": re.findall(
            ORDER_ID_PATTERN,
            text,
            re.IGNORECASE
        ),

        "error_codes": re.findall(
            ERROR_CODE_PATTERN,
            text,
            re.IGNORECASE
        ),

        "dates": re.findall(
            DATE_PATTERN,
            text
        ),

        "product_codes": re.findall(
            PRODUCT_CODE_PATTERN,
            text
        )
    }


# ============================================================
# NORMALIZE ORDER IDS
# ============================================================

def normalize_order_ids(text):
    """
    Normalize order IDs while preserving their identity.

    Example:
    ORDER-12345 -> ORD12345
    ORD-12345   -> ORD12345
    """

    if not text:
        return text

    def replace(match):
        value = match.group(0)

        value = (
            value
            .replace("-", "")
            .replace(" ", "")
            .upper()
        )

        if value.startswith("ORDER"):
            value = "ORD" + value[5:]

        return value

    return re.sub(
        ORDER_ID_PATTERN,
        replace,
        text,
        flags=re.IGNORECASE
    )


# ============================================================
# PRESERVE PROTECTED ENTITIES
# ============================================================

def protect_entities(text):
    """
    Replace protected entities with placeholders.

    This allows multilingual processing to operate on
    normal text without accidentally changing IDs/codes.
    """

    if not text:
        return {
            "text": text,
            "entities": {}
        }

    entities = {}

    patterns = {
        "ORDER": ORDER_ID_PATTERN,
        "ERROR": ERROR_CODE_PATTERN,
        "DATE": DATE_PATTERN,
        "PRODUCT": PRODUCT_CODE_PATTERN
    }

    protected_text = text

    counter = 0

    for entity_type, pattern in patterns.items():

        def replace(match):
            nonlocal counter

            key = f"__PROTECTED_{counter}__"

            entities[key] = match.group(0)

            counter += 1

            return key

        protected_text = re.sub(
            pattern,
            replace,
            protected_text,
            flags=re.IGNORECASE
        )

    return {
        "text": protected_text,
        "entities": entities
    }


# ============================================================
# RESTORE PROTECTED ENTITIES
# ============================================================

def restore_entities(text, entities):
    """
    Restore protected entities after multilingual processing.
    """

    if not text:
        return text

    if not entities:
        return text

    restored_text = text

    for placeholder, original_value in entities.items():

        restored_text = restored_text.replace(
            placeholder,
            original_value
        )

    return restored_text


# ============================================================
# NORMALIZE MULTILINGUAL MESSAGE
# ============================================================

def normalize_message(text):
    """
    Normalize a multilingual message while preserving
    important structured information.
    """

    if not text:
        return {
            "text": text,
            "protected_entities": {}
        }

    normalized_text = normalize_order_ids(text)

    protected = protect_entities(
        normalized_text
    )

    return {
        "text": protected["text"],
        "protected_entities":
            protected["entities"]
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("MULTILINGUAL NORMALIZATION TEST")
    print("=" * 60)

    sample = (
        "My order ORDER-12345 has error ERR-500 "
        "on 2026-09-20. Product code SM-G998B."
    )

    print("\nOriginal:")
    print(sample)

    result = normalize_message(sample)

    print("\nProtected text:")
    print(result["text"])

    print("\nProtected entities:")
    print(result["protected_entities"])

    restored = restore_entities(
        result["text"],
        result["protected_entities"]
    )

    print("\nRestored text:")
    print(restored)