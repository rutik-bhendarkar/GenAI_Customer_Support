from datetime import datetime


def check_escalation(
    sla_result: dict,
    high_risk: bool = False,
    unresolved_minutes: int = 0
):
    """
    Determine whether a support ticket should be escalated.
    """

    reasons = []

    # SLA breach
    if sla_result["status"] == "BREACHED":
        reasons.append("SLA deadline breached")

    # High-risk issue
    if high_risk:
        reasons.append("High-risk customer issue")

    # Unresolved negative conversation > 15 minutes
    if unresolved_minutes > 15:
        reasons.append(
            "Negative conversation unresolved for more than 15 minutes"
        )

    if reasons:
        return {
            "escalated": True,
            "status": "ESCALATED",
            "reasons": reasons,
            "escalated_at": datetime.now().isoformat()
        }

    return {
        "escalated": False,
        "status": "NORMAL",
        "reasons": [],
        "escalated_at": None
    }


if __name__ == "__main__":

    # Test 1: SLA breached
    sla = {
        "status": "BREACHED"
    }

    print("\nTest 1 - SLA Breach")
    print(check_escalation(sla))


    # Test 2: High-risk issue
    sla = {
        "status": "WITHIN_SLA"
    }

    print("\nTest 2 - High Risk")
    print(check_escalation(
        sla,
        high_risk=True
    ))


    # Test 3: Unresolved > 15 minutes
    print("\nTest 3 - Unresolved Conversation")
    print(check_escalation(
        sla,
        unresolved_minutes=20
    ))


    # Test 4: Normal ticket
    print("\nTest 4 - Normal")
    print(check_escalation(sla))