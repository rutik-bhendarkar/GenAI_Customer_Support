def calculate_priority(
    severity: str,
    sentiment: str,
    waiting_minutes: int = 0,
    customer_impact: str = "Low"
):
    """
    Calculate support ticket priority using:
    - Severity
    - Sentiment
    - Waiting time
    - Customer impact
    """

    score = 0

    # -----------------------------
    # 1. Severity
    # -----------------------------

    severity_scores = {
        "Low": 1,
        "Medium": 2,
        "High": 3,
        "Critical": 4
    }

    score += severity_scores.get(severity, 2)

    # -----------------------------
    # 2. Sentiment
    # -----------------------------

    sentiment_scores = {
        "Positive": 0,
        "Neutral": 0,
        "Negative": 1,
        "Frustrated": 2,
        "Urgent": 3
    }

    score += sentiment_scores.get(sentiment, 0)

    # -----------------------------
    # 3. Waiting Time
    # -----------------------------

    if waiting_minutes >= 60:
        score += 3

    elif waiting_minutes >= 30:
        score += 2

    elif waiting_minutes >= 15:
        score += 1

    # -----------------------------
    # 4. Customer Impact
    # -----------------------------

    impact_scores = {
        "Low": 0,
        "Medium": 1,
        "High": 2,
        "Critical": 3
    }

    score += impact_scores.get(customer_impact, 0)

    # -----------------------------
    # Final Priority
    # -----------------------------

    if score >= 9:
        priority = "CRITICAL"

    elif score >= 6:
        priority = "HIGH"

    elif score >= 3:
        priority = "MEDIUM"

    else:
        priority = "LOW"

    return {
        "priority": priority,
        "score": score
    }


# -----------------------------
# Testing
# -----------------------------

if __name__ == "__main__":

    tests = [
        {
            "severity": "Low",
            "sentiment": "Positive",
            "waiting_minutes": 5,
            "customer_impact": "Low"
        },
        {
            "severity": "Medium",
            "sentiment": "Negative",
            "waiting_minutes": 20,
            "customer_impact": "Medium"
        },
        {
            "severity": "High",
            "sentiment": "Frustrated",
            "waiting_minutes": 40,
            "customer_impact": "High"
        },
        {
            "severity": "Critical",
            "sentiment": "Urgent",
            "waiting_minutes": 70,
            "customer_impact": "Critical"
        }
    ]

    for test in tests:

        result = calculate_priority(**test)

        print("\nInput:")
        print(test)

        print("Result:")
        print(result)