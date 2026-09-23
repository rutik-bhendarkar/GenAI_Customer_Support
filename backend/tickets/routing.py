from typing import Dict


# ==========================================
# AGENT CONFIGURATION
# ==========================================

AGENTS = [
    {
        "id": "AG001",
        "name": "Agent Rahul",
        "skills": ["delivery", "order"],
        "available": True,
        "on_call": False,
        "workload": 2
    },
    {
        "id": "AG002",
        "name": "Agent Priya",
        "skills": ["payment", "refund"],
        "available": True,
        "on_call": False,
        "workload": 1
    },
    {
        "id": "AG003",
        "name": "Agent Amit",
        "skills": ["technical", "product"],
        "available": True,
        "on_call": False,
        "workload": 4
    },
    {
        "id": "AG004",
        "name": "Agent Neha",
        "skills": ["account", "security"],
        "available": False,
        "on_call": True,
        "workload": 0
    }
]


# ==========================================
# DETERMINE REQUIRED SKILL
# ==========================================

def determine_required_skill(issue: str) -> str:

    issue = issue.lower()

    if any(
        word in issue
        for word in [
            "delivery",
            "delivered",
            "arrived",
            "order",
            "shipping",
            "shipment",
            "tracking"
        ]
    ):
        return "delivery"

    if any(
        word in issue
        for word in [
            "payment",
            "charged",
            "refund",
            "transaction"
        ]
    ):
        return "payment"

    if any(
        word in issue
        for word in [
            "hacked",
            "account",
            "password",
            "login",
            "security",
            "unauthorized"
        ]
    ):
        return "account"

    if any(
        word in issue
        for word in [
            "technical",
            "broken",
            "not working",
            "defective"
        ]
    ):
        return "technical"

    return "general"


# ==========================================
# ROUTE NORMAL TICKET
# ==========================================

def route_ticket(
    issue: str,
    priority: str = "MEDIUM",
    support_queue: str = "NORMAL_SUPPORT"
) -> Dict:

    required_skill = determine_required_skill(issue)

    # ======================================
    # ON-CALL ROUTING
    # ======================================

    if support_queue == "ON_CALL":

        on_call_agents = [
            agent
            for agent in AGENTS
            if agent["on_call"]
            and required_skill in agent["skills"]
        ]

        if on_call_agents:

            selected_agent = min(
                on_call_agents,
                key=lambda agent: agent["workload"]
            )

            return {
                "assigned": True,
                "agent": selected_agent["name"],
                "agent_id": selected_agent["id"],
                "required_skill": required_skill,
                "workload": selected_agent["workload"],
                "queue": "ON_CALL",
                "reason": "Urgent ticket assigned to available on-call agent."
            }

        return {
            "assigned": False,
            "agent": None,
            "agent_id": None,
            "required_skill": required_skill,
            "workload": None,
            "queue": "ON_CALL",
            "reason": "No suitable on-call agent is available."
        }

    # ======================================
    # NORMAL ROUTING
    # ======================================

    suitable_agents = [
        agent
        for agent in AGENTS
        if agent["available"]
        and required_skill in agent["skills"]
    ]

    # ======================================
    # NO AVAILABLE AGENT
    # ======================================

    if not suitable_agents:

        return {
            "assigned": False,
            "agent": None,
            "agent_id": None,
            "required_skill": required_skill,
            "workload": None,
            "queue": support_queue,
            "reason": "No available agent with the required skill."
        }

    # ======================================
    # LOWEST WORKLOAD
    # ======================================

    selected_agent = min(
        suitable_agents,
        key=lambda agent: agent["workload"]
    )

    return {
        "assigned": True,
        "agent": selected_agent["name"],
        "agent_id": selected_agent["id"],
        "required_skill": required_skill,
        "workload": selected_agent["workload"],
        "queue": support_queue,
        "reason": "Ticket assigned to available agent with lowest workload."
    }


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    print("\n================================")
    print("TEST 1 - Normal Delivery")
    print("================================")

    print(
        route_ticket(
            issue="Order has not arrived",
            priority="MEDIUM",
            support_queue="NORMAL_SUPPORT"
        )
    )


    print("\n================================")
    print("TEST 2 - Payment")
    print("================================")

    print(
        route_ticket(
            issue="Customer was charged twice",
            priority="HIGH",
            support_queue="NORMAL_SUPPORT"
        )
    )


    print("\n================================")
    print("TEST 3 - Technical")
    print("================================")

    print(
        route_ticket(
            issue="My laptop is broken",
            priority="MEDIUM",
            support_queue="NORMAL_SUPPORT"
        )
    )


    print("\n================================")
    print("TEST 4 - On Call Security")
    print("================================")

    print(
        route_ticket(
            issue="Someone hacked my account",
            priority="CRITICAL",
            support_queue="ON_CALL"
        )
    )


    print("\n================================")
    print("TEST 5 - Unavailable Skill")
    print("================================")

    print(
        route_ticket(
            issue="Account security problem",
            priority="CRITICAL",
            support_queue="NORMAL_SUPPORT"
        )
    )