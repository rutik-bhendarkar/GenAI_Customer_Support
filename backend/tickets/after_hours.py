from datetime import datetime, time, date, timedelta


# ==========================================
# BUSINESS HOURS CONFIGURATION
# ==========================================

BUSINESS_START_HOUR = 9
BUSINESS_END_HOUR = 18

WORKING_DAYS = {0, 1, 2, 3, 4}

HOLIDAYS = {
    # date(2026, 10, 2),
    # date(2026, 12, 25),
}


# ==========================================
# BUSINESS DAY CHECK
# ==========================================

def is_business_day(current_date: date) -> bool:

    if current_date.weekday() not in WORKING_DAYS:
        return False

    if current_date in HOLIDAYS:
        return False

    return True


# ==========================================
# BUSINESS HOURS CHECK
# ==========================================

def is_business_hours(current_time: datetime) -> bool:

    if not is_business_day(current_time.date()):
        return False

    start = time(BUSINESS_START_HOUR, 0)
    end = time(BUSINESS_END_HOUR, 0)

    return start <= current_time.time() < end


# ==========================================
# NEXT WORKING DAY
# ==========================================

def get_next_business_day(current_date: date):

    next_day = current_date + timedelta(days=1)

    while not is_business_day(next_day):
        next_day += timedelta(days=1)

    return next_day


# ==========================================
# AFTER-HOURS QUEUE DECISION
# ==========================================

def determine_support_queue(
    priority: str,
    high_risk: bool,
    current_time: datetime = None
):

    if current_time is None:
        current_time = datetime.now()

    # --------------------------------------
    # During business hours
    # --------------------------------------

    if is_business_hours(current_time):

        return {
            "after_hours": False,
            "queue": "NORMAL_SUPPORT",
            "handling": "Process during business hours.",
            "next_working_day": None
        }

    # --------------------------------------
    # Outside business hours
    # --------------------------------------

    if high_risk or priority.upper() in [
        "CRITICAL",
        "HIGH"
    ]:

        return {
            "after_hours": True,
            "queue": "ON_CALL",
            "handling": "Urgent issue routed to on-call queue.",
            "next_working_day": None
        }

    # --------------------------------------
    # Normal after-hours complaint
    # --------------------------------------

    next_day = get_next_business_day(
        current_time.date()
    )

    return {
        "after_hours": True,
        "queue": "NEXT_WORKING_DAY",
        "handling": "Normal complaint scheduled for next working day.",
        "next_working_day": next_day.isoformat()
    }


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    # 10 AM Wednesday
    business_time = datetime(
        2026, 9, 16, 10, 0
    )

    # 8 PM Wednesday
    after_hours = datetime(
        2026, 9, 16, 20, 0
    )

    print("\nTEST 1 - Business Hours")
    print(
        determine_support_queue(
            priority="MEDIUM",
            high_risk=False,
            current_time=business_time
        )
    )

    print("\nTEST 2 - After Hours Normal")
    print(
        determine_support_queue(
            priority="MEDIUM",
            high_risk=False,
            current_time=after_hours
        )
    )

    print("\nTEST 3 - After Hours Urgent")
    print(
        determine_support_queue(
            priority="HIGH",
            high_risk=False,
            current_time=after_hours
        )
    )

    print("\nTEST 4 - After Hours High Risk")
    print(
        determine_support_queue(
            priority="MEDIUM",
            high_risk=True,
            current_time=after_hours
        )
    )