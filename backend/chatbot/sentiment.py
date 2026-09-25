# backend/chatbot/sentiment.py

def analyze_sentiment(message: str):
    """
    Lightweight sentiment analysis for deployment.

    This version does not load Hugging Face Transformers/PyTorch,
    which keeps memory usage low on Render's 512 MB instance.
    """

    text = message.lower().strip()

    # -----------------------------
    # HIGH-RISK PATTERNS
    # -----------------------------
    high_risk_words = [
        "hacked",
        "hack",
        "account compromised",
        "unauthorized payment",
        "unauthorized transaction",
        "duplicate payment",
        "fraud",
        "stolen account",
        "payment information was stolen",
        "legal action",
        "legal threat"
    ]

    # -----------------------------
    # URGENT PATTERNS
    # -----------------------------
    urgent_words = [
        "urgent",
        "urgently",
        "immediately",
        "asap",
        "emergency",
        "right now",
        "help now"
    ]

    # -----------------------------
    # FRUSTRATION PATTERNS
    # -----------------------------
    frustrated_words = [
        "frustrated",
        "extremely frustrating",
        "nobody helped",
        "no one helped",
        "contacted support three times",
        "contacted support multiple times",
        "still not resolved",
        "fed up",
        "sick of",
        "terrible service",
        "worst service",
        "ridiculous"
    ]

    # -----------------------------
    # SARCASM PATTERNS
    # -----------------------------
    sarcastic_patterns = [
        "great, another",
        "great another",
        "exactly what i needed",
        "just what i needed",
        "thanks for nothing",
        "wonderful, another",
        "perfect, another",
        "what a surprise",
        "love waiting",
        "love being"
    ]

    # -----------------------------
    # POSITIVE PATTERNS
    # -----------------------------
    positive_phrases = [
        "thank you",
        "thanks",
        "issue is solved",
        "problem is solved",
        "problem solved",
        "issue resolved",
        "problem resolved",
        "working now",
        "works now",
        "appreciate your help",
        "great help",
        "very helpful",
        "everything is fine",
        "everything works"
    ]

    # -----------------------------
    # NEGATIVE PATTERNS
    # -----------------------------
    negative_words = [
        "not working",
        "not received",
        "not arrived",
        "delayed",
        "late",
        "problem",
        "failed",
        "failure",
        "broken",
        "damaged",
        "wrong",
        "missing",
        "complaint",
        "stolen",
        "hacked",
        "fraud",
        "unauthorized"
    ]

    # -----------------------------
    # NEUTRAL PATTERNS
    # -----------------------------
    neutral_phrases = [
        "i want to know",
        "i would like to know",
        "can you tell me",
        "could you tell me",
        "what is the status",
        "what's the status",
        "status of my order",
        "where is my order",
        "when will my order arrive",
        "please provide information",
        "i need information",
        "i need to know",
        "can i know",
        "tell me about",
        "what are the details"
    ]

    # -----------------------------
    # DETECTION
    # -----------------------------
    high_risk = any(
        phrase in text for phrase in high_risk_words
    )

    sarcastic = any(
        phrase in text for phrase in sarcastic_patterns
    )

    frustrated = any(
        phrase in text for phrase in frustrated_words
    )

    urgent = any(
        phrase in text for phrase in urgent_words
    )

    positive = any(
        phrase in text for phrase in positive_phrases
    )

    negative = any(
        phrase in text for phrase in negative_words
    )

    neutral = any(
        phrase in text for phrase in neutral_phrases
    )

    # -----------------------------
    # SENTIMENT DECISION
    # -----------------------------

    # 1. High-risk
    if high_risk:
        sentiment = "NEGATIVE"
        category = "Negative"
        confidence = 0.95

    # 2. Sarcasm
    elif sarcastic:
        sentiment = "NEGATIVE"
        category = "Sarcastic"
        confidence = 0.90

    # 3. Frustration
    elif frustrated:
        sentiment = "NEGATIVE"
        category = "Frustrated"
        confidence = 0.90

    # 4. Urgent
    elif urgent:
        sentiment = "NEGATIVE"
        category = "Urgent"
        confidence = 0.90

    # 5. Explicit positive
    elif positive:
        sentiment = "POSITIVE"
        category = "Positive"
        confidence = 0.90

    # 6. Explicit negative
    elif negative:
        sentiment = "NEGATIVE"
        category = "Negative"
        confidence = 0.85

    # 7. Explicit neutral
    elif neutral:
        sentiment = "NEUTRAL"
        category = "Neutral"
        confidence = 0.85

    # 8. Default
    else:
        sentiment = "NEUTRAL"
        category = "Neutral"
        confidence = 0.60

    return {
        "sentiment": sentiment,
        "category": category,
        "confidence": confidence,
        "high_risk": high_risk
    }