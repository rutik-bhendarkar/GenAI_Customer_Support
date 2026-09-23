from transformers import pipeline


sentiment_pipeline = pipeline(
    "sentiment-analysis",
    model="distilbert-base-uncased-finetuned-sst-2-english"
)


def analyze_sentiment(message: str):
    text = message.lower().strip()

    result = sentiment_pipeline(message)[0]

    model_sentiment = result["label"]
    confidence = round(float(result["score"]), 4)

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
    neutral = any(
        phrase in text for phrase in neutral_phrases
)
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

    # -----------------------------
    # SENTIMENT DECISION
    # -----------------------------

    # 1. High-risk always takes highest priority
    if high_risk:
        sentiment = "NEGATIVE"
        category = "Negative"
        confidence = max(confidence, 0.90)

    # 2. Sarcasm
    elif sarcastic:
        sentiment = "NEGATIVE"
        category = "Sarcastic"
        confidence = max(confidence, 0.85)

    # 3. Frustration
    elif frustrated:
        sentiment = "NEGATIVE"
        category = "Frustrated"

    # 4. Urgent
    elif urgent:
        sentiment = "NEGATIVE"
        category = "Urgent"
        confidence = max(confidence, 0.90)

    # 5. Explicit positive
    elif positive:
        sentiment = "POSITIVE"
        category = "Positive"

    # 6. Explicit negative
    elif negative:
        sentiment = "NEGATIVE"
        category = "Negative"

    elif neutral:
       
       sentiment = "NEUTRAL"
       category = "Neutral"

    # 7. Model result
    elif model_sentiment == "POSITIVE":
        sentiment = "POSITIVE"
        category = "Positive"

    elif model_sentiment == "NEGATIVE":
        sentiment = "NEGATIVE"
        category = "Negative"

    # 8. Neutral
    else:
        sentiment = "NEUTRAL"
        category = "Neutral"

    return {
        "sentiment": sentiment,
        "category": category,
        "confidence": confidence,
        "high_risk": high_risk
    }