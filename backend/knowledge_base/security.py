import re


# ==========================================
# EMAIL MASKING
# ==========================================

def mask_email(text: str) -> str:
    """
    Mask email addresses.

    example:
    user@gmail.com
    -> u***@gmail.com
    """

    pattern = r"\b([A-Za-z0-9._%+-])([A-Za-z0-9._%+-]*)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b"

    def replace(match):
        first_character = match.group(1)
        domain = match.group(3)

        return f"{first_character}***@{domain}"

    return re.sub(pattern, replace, text)


# ==========================================
# PHONE MASKING
# ==========================================

def mask_phone(text: str) -> str:
    """
    Mask phone numbers while keeping
    the last four digits visible.
    """

    pattern = r"(?<!\d)(?:\+?\d[\d\s-]{7,}\d)(?!\d)"

    def replace(match):

        number = re.sub(
            r"\D",
            "",
            match.group()
        )

        if len(number) < 10:
            return match.group()

        return "*" * (len(number) - 4) + number[-4:]

    return re.sub(pattern, replace, text)


# ==========================================
# CARD NUMBER MASKING
# ==========================================

def mask_card_number(text: str) -> str:
    """
    Mask payment card numbers.
    """

    pattern = r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)"

    def replace(match):

        number = re.sub(
            r"\D",
            "",
            match.group()
        )

        if len(number) < 13:
            return match.group()

        return "*" * (len(number) - 4) + number[-4:]

    return re.sub(pattern, replace, text)


# ==========================================
# OTP MASKING
# ==========================================

def mask_otp(text: str) -> str:
    """
    Mask common OTP formats.
    """

    pattern = (
        r"(?i)"
        r"(otp|one[- ]time password)"
        r"(\s*(is|:|-|=)\s*)"
        r"\d{4,8}"
    )

    def replace(match):

        label = match.group(1)
        separator = match.group(2)

        return f"{label}{separator}******"

    return re.sub(
        pattern,
        replace,
        text
    )


# ==========================================
# MASK ALL SENSITIVE DATA
# ==========================================

def mask_sensitive_data(text: str) -> str:
    """
    Apply all sensitive-data masking rules.
    """

    text = mask_email(text)
    text = mask_phone(text)
    text = mask_card_number(text)
    text = mask_otp(text)

    return text


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    test_text = (
        "Customer email is rutik@example.com. "
        "Phone is 9876543210. "
        "Card number is 4111 1111 1111 1111. "
        "OTP is 123456."
    )

    print("\nSensitive Data Protection")
    print("=========================")

    print("\nOriginal:")
    print(test_text)

    masked_text = mask_sensitive_data(
        test_text
    )

    print("\nMasked:")
    print(masked_text)