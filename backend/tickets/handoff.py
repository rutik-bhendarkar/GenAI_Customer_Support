import re
from typing import Dict


# ==========================================
# MASK SENSITIVE INFORMATION
# ==========================================

def mask_email(email: str) -> str:
    """
    Mask an email address.
    """

    if not email:
        return email

    parts = email.split("@")

    if len(parts) != 2:
        return "***"

    username = parts[0]
    domain = parts[1]

    if len(username) <= 2:
        masked_username = "*" * len(username)
    else:
        masked_username = (
            username[0]
            + "*" * (len(username) - 2)
            + username[-1]
        )

    return masked_username + "@" + domain


def mask_phone(phone: str) -> str:
    """
    Mask a phone number.
    """

    if not phone:
        return phone

    digits = re.sub(r"\D", "", phone)

    if len(digits) < 4:
        return "***"

    return "*" * (len(digits) - 4) + digits[-4:]


def mask_contact_details(contact: str) -> str:
    """
    Detect and mask email or phone.
    """

    if not contact:
        return contact

    if "@" in contact:
        return mask_email(contact)

    return mask_phone(contact)


# ==========================================
# GENERATE HANDOFF SUMMARY
# ==========================================

def generate_handoff_summary(ticket: Dict) -> Dict:
    """
    Generate a concise masked summary for
    another support agent/team.
    """

    customer = ticket.get("customer")

    order_id = ticket.get("order_id")

    issue = ticket.get("issue")

    sentiment = ticket.get("sentiment")

    severity = ticket.get("severity")

    priority = ticket.get("priority")

    contact = ticket.get("contact_details")

    masked_contact = mask_contact_details(contact)

    summary = (
        f"Customer {customer or 'Unknown'} "
        f"reported: {issue}. "
        f"Order: {order_id or 'Not provided'}. "
        f"Sentiment: {sentiment or 'Unknown'}. "
        f"Severity: {severity or 'Unknown'}. "
        f"Priority: {priority or 'Unknown'}."
    )

    return {
        "ticket_id": ticket.get("ticket_id"),
        "summary": summary,
        "customer": customer,
        "order_id": order_id,
        "masked_contact": masked_contact,
        "priority": priority,
        "severity": severity
    }


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    test_ticket = {
        "ticket_id": "TKT-0001",
        "customer": "Rahul",
        "order_id": "ORD12345",
        "issue": "Order has not arrived",
        "sentiment": "Frustrated",
        "severity": "High",
        "priority": "HIGH",
        "contact_details": "9876543210"
    }

    result = generate_handoff_summary(test_ticket)

    print("\nHandoff Summary:")
    print(result)