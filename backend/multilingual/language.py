# ============================================================
# MULTILINGUAL LANGUAGE DETECTION
# ============================================================

import re


# ============================================================
# CONFIGURATION
# ============================================================

SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi"
}


# ============================================================
# LANGUAGE PATTERNS
# ============================================================

HINDI_PATTERN = re.compile(
    r"[\u0900-\u097F]"
)

MARATHI_PATTERN = re.compile(
    r"[\u0900-\u097F]"
)


# Common Hindi/Marathi words used as supporting signals.
HINDI_WORDS = {
    "है",
    "हूँ",
    "मेरा",
    "मेरी",
    "मुझे",
    "चाहिए",
    "क्यों",
    "कब",
    "नहीं",
    "भुगतान",
    "ऑर्डर",
    "रिफंड",
    "समस्या"
}


MARATHI_WORDS = {
    "आहे",
    "माझा",
    "माझी",
    "मला",
    "पाहिजे",
    "का",
    "कधी",
    "नाही",
    "पेमेंट",
    "ऑर्डर",
    "परतावा",
    "समस्या"
}


# ============================================================
# LANGUAGE DETECTION
# ============================================================

def detect_language(text):
    """
    Detect the likely language of a customer message.

    Supported:
    - English
    - Hindi
    - Marathi

    Returns:
        {
            "language_code": "en",
            "language": "English",
            "confidence": 0.95
        }
    """

    if not text or not text.strip():

        return {
            "language_code": None,
            "language": None,
            "confidence": 0.0
        }

    words = text.lower().split()

    hindi_score = 0
    marathi_score = 0

    for word in words:

        cleaned = re.sub(
            r"[^\w\u0900-\u097F]",
            "",
            word
        )

        if cleaned in HINDI_WORDS:
            hindi_score += 1

        if cleaned in MARATHI_WORDS:
            marathi_score += 1

    # --------------------------------------------------------
    # Devanagari language detection
    # --------------------------------------------------------

    devanagari_characters = len(
        HINDI_PATTERN.findall(text)
    )

    # If there is no Devanagari text, treat it as English.
    if devanagari_characters == 0:

        return {
            "language_code": "en",
            "language": "English",
            "confidence": 0.95
        }

    # --------------------------------------------------------
    # Hindi vs Marathi
    # --------------------------------------------------------

    if marathi_score > hindi_score:

        confidence = min(
            0.60 + (marathi_score * 0.10),
            0.99
        )

        return {
            "language_code": "mr",
            "language": "Marathi",
            "confidence": confidence
        }

    if hindi_score > marathi_score:

        confidence = min(
            0.60 + (hindi_score * 0.10),
            0.99
        )

        return {
            "language_code": "hi",
            "language": "Hindi",
            "confidence": confidence
        }

    # --------------------------------------------------------
    # Ambiguous Devanagari
    # --------------------------------------------------------

    return {
        "language_code": None,
        "language": "Ambiguous",
        "confidence": 0.40
    }


# ============================================================
# SUPPORTED LANGUAGE CHECK
# ============================================================

def is_supported_language(language_code):
    """
    Check whether a detected language is supported.
    """

    return language_code in SUPPORTED_LANGUAGES


# ============================================================
# LOW-CONFIDENCE CHECK
# ============================================================

def requires_language_clarification(
    detection_result,
    threshold=0.60
):
    """
    Determine whether language clarification is required.
    """

    if not detection_result:
        return True

    language_code = detection_result.get(
        "language_code"
    )

    confidence = detection_result.get(
        "confidence",
        0.0
    )

    if not language_code:
        return True

    if not is_supported_language(
        language_code
    ):
        return True

    return confidence < threshold


# ============================================================
# LANGUAGE RESPONSE
# ============================================================

def get_language_response(
    text,
    threshold=0.75
):
    """
    Detect language and determine whether
    clarification is required.
    """

    result = detect_language(text)

    if result["confidence"] < threshold:

        return {
            "requires_clarification": True,
            "message": (
                "I'm not fully confident about the language. "
                "Could you please clarify or rephrase your message?"
            ),
            "detection": result
        }

    return {
        "requires_clarification": False,
        "message": None,
        "detection": result
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("MULTILINGUAL LANGUAGE DETECTION")
    print("=" * 60)

    test_messages = [
        "My order is not working.",
        "मेरा ऑर्डर काम नहीं कर रहा है।",
        "माझा ऑर्डर काम करत नाही आहे."
    ]

    for message in test_messages:

        result = detect_language(message)

        print("\nMessage:")
        print(message)

        print("Detection:")
        print(result)

        print(
            "Needs clarification:",
            requires_language_clarification(result)
        )

    # --------------------------------------------------------
    # LOW-CONFIDENCE TEST
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("LOW-CONFIDENCE CLARIFICATION TEST")
    print("=" * 60)

    low_confidence_messages = [
        "order please",
        "help",
        "payment",
        "??",
        "माझा"
    ]

    for message in low_confidence_messages:

        response = get_language_response(message)

        print("\nMessage:", message)
        print("Response:", response)