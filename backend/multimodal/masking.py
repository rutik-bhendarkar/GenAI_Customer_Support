import re


def mask_phone_numbers(text):
    """
    Mask phone numbers while keeping the last 4 digits.
    Example: 9876543210 -> ******3210
    """

    if not text:
        return text

    pattern = r"\b\d{10}\b"

    def replace(match):
        number = match.group(0)
        return "*" * 6 + number[-4:]

    return re.sub(pattern, replace, text)


def mask_email_addresses(text):
    """
    Mask email addresses.

    Example:
    user@gmail.com -> u***@gmail.com
    """

    if not text:
        return text

    pattern = r"\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b"

    def replace(match):
        username = match.group(1)
        domain = match.group(2)

        if len(username) <= 1:
            masked_username = "*"
        else:
            masked_username = (
                username[0] +
                "*" * min(3, len(username) - 1)
            )

        return f"{masked_username}@{domain}"

    return re.sub(
        pattern,
        replace,
        text
    )


def mask_payment_information(text):
    """
    Mask common card-number formats.

    Example:
    4111 1111 1111 1111 -> **** **** **** 1111
    """

    if not text:
        return text

    pattern = r"\b(?:\d{4}[- ]?){3}\d{4}\b"

    def replace(match):
        digits = re.sub(
            r"[- ]",
            "",
            match.group(0)
        )

        return (
            "**** **** **** " +
            digits[-4:]
        )

    return re.sub(
        pattern,
        replace,
        text
    )


def mask_sensitive_data(text):
    """
    Apply all sensitive-data masking rules.
    """

    if not text:
        return text

    text = mask_phone_numbers(text)
    text = mask_email_addresses(text)
    text = mask_payment_information(text)

    return text


if __name__ == "__main__":

    sample = """
    Customer phone: 9876543210
    Email: customer@gmail.com
    Card: 4111 1111 1111 1111
    """

    print("Original:")
    print(sample)

    print("Masked:")
    print(mask_sensitive_data(sample))