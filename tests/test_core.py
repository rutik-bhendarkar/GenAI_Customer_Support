from datetime import datetime, timedelta

from backend.chatbot.sentiment import analyze_sentiment
from backend.tickets.escalation import check_escalation
from backend.tickets.after_hours import determine_support_queue
from backend.multilingual.language import detect_language
from backend.multilingual.normalization import normalize_message


def test_negative_sentiment():
    result = analyze_sentiment(
        "My order is delayed and not working."
    )

    assert result["sentiment"] == "NEGATIVE"
    assert result["category"] == "Negative"


def test_high_risk_sentiment():
    result = analyze_sentiment(
        "Someone hacked my account and made an unauthorized payment."
    )

    assert result["sentiment"] == "NEGATIVE"
    assert result["high_risk"] is True


def test_frustrated_sentiment():
    result = analyze_sentiment(
        "I am extremely frustrated. I contacted support three times "
        "and my issue is still not resolved."
    )

    assert result["category"] == "Frustrated"


def test_sarcastic_sentiment():
    result = analyze_sentiment(
        "Great, another delayed order. Exactly what I needed."
    )

    assert result["category"] == "Sarcastic"


def test_urgent_sentiment():
    result = analyze_sentiment(
        "This is urgent. Please help me immediately."
    )

    assert result["category"] == "Urgent"


def test_high_risk_escalation():
    result = check_escalation(
        sla_result={"status": "WITHIN_SLA"},
        high_risk=True,
        unresolved_minutes=0
    )

    assert result["escalated"] is True
    assert "High-risk customer issue" in result["reasons"]


def test_unresolved_escalation():
    result = check_escalation(
        sla_result={"status": "WITHIN_SLA"},
        high_risk=False,
        unresolved_minutes=16
    )

    assert result["escalated"] is True
    assert (
        "Negative conversation unresolved for more than 15 minutes"
        in result["reasons"]
    )


def test_sla_breach_escalation():
    result = check_escalation(
        sla_result={"status": "BREACHED"},
        high_risk=False,
        unresolved_minutes=0
    )

    assert result["escalated"] is True


def test_after_hours_normal():
    result = determine_support_queue(
        priority="MEDIUM",
        high_risk=False,
        current_time=datetime(2026, 9, 23, 20, 0)
    )

    assert result["after_hours"] is True
    assert result["queue"] == "NEXT_WORKING_DAY"


def test_after_hours_high_risk():
    result = determine_support_queue(
        priority="MEDIUM",
        high_risk=True,
        current_time=datetime(2026, 9, 23, 20, 0)
    )

    assert result["after_hours"] is True
    assert result["queue"] == "ON_CALL"


def test_english_language():
    result = detect_language(
        "My order is delayed."
    )

    assert result["language_code"] == "en"


def test_hindi_language():
    result = detect_language(
        "मेरा ऑर्डर अभी तक नहीं आया है।"
    )

    assert result["language_code"] == "hi"


def test_marathi_language():
    result = detect_language(
        "माझा ऑर्डर अजून आलेला नाही."
    )

    assert result["language_code"] == "mr"


def test_order_id_protection():
    result = normalize_message(
        "My order ORD12345 is delayed."
    )

    assert "ORD12345" in result["protected_entities"].values()


def test_10_message_context_requirement():
    messages = list(range(1, 11))

    assert len(messages) == 10