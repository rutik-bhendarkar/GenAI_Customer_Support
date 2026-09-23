from datetime import datetime, timedelta, time, date


# ==============================
# CONFIGURATION
# ==============================

BUSINESS_START_HOUR = 9
BUSINESS_END_HOUR = 18

# Monday = 0 ... Sunday = 6
WORKING_DAYS = {0, 1, 2, 3, 4}

# Add holidays here when required
HOLIDAYS = {
    # date(2026, 10, 2),
    # date(2026, 12, 25),
}


# SLA duration in business minutes
SLA_MINUTES = {
    "CRITICAL": 60,
    "HIGH": 120,
    "MEDIUM": 240,
    "LOW": 480
}


# ==============================
# BUSINESS DAY FUNCTIONS
# ==============================

def is_business_day(current_date: date) -> bool:
    """
    Check whether the given date is a working day.
    """

    if current_date.weekday() not in WORKING_DAYS:
        return False

    if current_date in HOLIDAYS:
        return False

    return True


def get_business_start(current_date: date):
    return datetime.combine(
        current_date,
        time(BUSINESS_START_HOUR, 0)
    )


def get_business_end(current_date: date):
    return datetime.combine(
        current_date,
        time(BUSINESS_END_HOUR, 0)
    )


def get_next_business_day(current_date: date):
    """
    Return the next working day.
    """

    next_day = current_date + timedelta(days=1)

    while not is_business_day(next_day):
        next_day += timedelta(days=1)

    return next_day


# ==============================
# NORMALIZE TIME
# ==============================

def normalize_to_business_time(start_time: datetime):
    """
    Move a datetime into valid business hours.
    """

    current = start_time

    # Weekend / holiday
    while not is_business_day(current.date()):
        next_day = get_next_business_day(current.date())

        current = get_business_start(next_day)

    business_start = get_business_start(current.date())
    business_end = get_business_end(current.date())

    # Before business hours
    if current < business_start:
        current = business_start

    # After business hours
    elif current >= business_end:

        next_day = get_next_business_day(current.date())

        current = get_business_start(next_day)

    return current


# ==============================
# ADD BUSINESS MINUTES
# ==============================

def add_business_minutes(start_time: datetime, minutes: int):
    """
    Add SLA time while excluding weekends,
    holidays and non-working hours.
    """

    current = normalize_to_business_time(start_time)

    remaining = minutes

    while remaining > 0:

        business_end = get_business_end(current.date())

        available_minutes = int(
            (business_end - current).total_seconds() / 60
        )

        # SLA finishes today
        if remaining <= available_minutes:

            return current + timedelta(
                minutes=remaining
            )

        # Consume today's remaining business time
        remaining -= available_minutes

        # Move to next business day
        next_day = get_next_business_day(current.date())

        current = get_business_start(next_day)

    return current


# ==============================
# CALCULATE SLA
# ==============================

def calculate_sla(
    priority: str,
    created_at: datetime = None,
    current_time: datetime = None
):
    """
    Calculate SLA deadline and 75% warning time.
    """

    priority = priority.upper()

    sla_minutes = SLA_MINUTES.get(
        priority,
        SLA_MINUTES["MEDIUM"]
    )

    if created_at is None:
        created_at = datetime.now()

    if current_time is None:
        current_time = datetime.now()

    # Make sure SLA starts during business hours
    sla_start = normalize_to_business_time(created_at)

    # SLA deadline
    deadline = add_business_minutes(
        sla_start,
        sla_minutes
    )

    # 75% warning point
    warning_minutes = int(sla_minutes * 0.75)

    warning_time = add_business_minutes(
        sla_start,
        warning_minutes
    )

    # Determine SLA status
    if current_time >= deadline:

        status = "BREACHED"

    elif current_time >= warning_time:

        status = "WARNING"

    else:

        status = "WITHIN_SLA"

    return {
        "priority": priority,
        "sla_minutes": sla_minutes,
        "sla_start": sla_start.isoformat(),
        "warning_time": warning_time.isoformat(),
        "deadline": deadline.isoformat(),
        "status": status
    }


# ==============================
# TEST
# ==============================

if __name__ == "__main__":

    print("\n================================")
    print("TEST 1 - WITHIN SLA")
    print("================================")

    created = datetime(2026, 9, 16, 10, 0)

    result = calculate_sla(
        priority="HIGH",
        created_at=created,
        current_time=datetime(2026, 9, 16, 10, 30)
    )

    print(result)


    print("\n================================")
    print("TEST 2 - SLA WARNING")
    print("================================")

    result = calculate_sla(
        priority="HIGH",
        created_at=created,
        current_time=datetime(2026, 9, 16, 11, 40)
    )

    print(result)


    print("\n================================")
    print("TEST 3 - SLA BREACHED")
    print("================================")

    result = calculate_sla(
        priority="HIGH",
        created_at=created,
        current_time=datetime(2026, 9, 16, 12, 30)
    )

    print(result)


    print("\n================================")
    print("TEST 4 - AFTER HOURS")
    print("================================")

    created_after_hours = datetime(
        2026, 9, 16, 20, 0
    )

    result = calculate_sla(
        priority="MEDIUM",
        created_at=created_after_hours,
        current_time=datetime(2026, 9, 17, 10, 0)
    )

    print(result)