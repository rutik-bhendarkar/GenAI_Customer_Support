import time


# ==========================================
# RETRY CONFIGURATION
# ==========================================

RETRY_DELAYS_MINUTES = [15, 30, 60]


# ==========================================
# EXECUTE OPERATION WITH RETRIES
# ==========================================

def execute_with_retry(
    operation,
    retry_delays=None,
    sleep_function=None
):
    """
    Execute an operation with configurable retries.

    Default retry delays:
        15 minutes
        30 minutes
        60 minutes

    sleep_function can be replaced during testing
    so the test does not actually wait.
    """

    if retry_delays is None:
        retry_delays = RETRY_DELAYS_MINUTES

    if sleep_function is None:
        sleep_function = time.sleep

    attempts = 0
    retry_history = []

    # Initial attempt + configured retries
    max_attempts = len(retry_delays) + 1

    while attempts < max_attempts:

        attempts += 1

        try:
            result = operation()

            if result.get("success", False):

                return {
                    "success": True,
                    "attempts": attempts,
                    "retry_history": retry_history,
                    "result": result
                }

        except Exception as error:

            result = {
                "success": False,
                "status": "ERROR",
                "error": str(error)
            }

        # No more retries available
        if attempts > len(retry_delays):

            return {
                "success": False,
                "attempts": attempts,
                "retry_history": retry_history,
                "result": result,
                "status": "RETRY_LIMIT_REACHED"
            }

        delay_minutes = retry_delays[attempts - 1]

        retry_history.append({
            "attempt": attempts,
            "next_attempt": attempts + 1,
            "delay_minutes": delay_minutes,
            "status": "RETRY_SCHEDULED"
        })

        print(
            f"Retry scheduled: "
            f"{delay_minutes} minutes"
        )

        # Convert minutes to seconds
        sleep_seconds = delay_minutes * 60

        sleep_function(sleep_seconds)


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    print("=" * 50)
    print("RETRY MECHANISM TEST")
    print("=" * 50)

    attempt_counter = {
        "count": 0
    }

    def failing_operation():

        attempt_counter["count"] += 1

        print(
            f"Operation attempt "
            f"{attempt_counter['count']}"
        )

        # First 3 attempts fail
        if attempt_counter["count"] <= 3:

            return {
                "success": False,
                "status": "TEMPORARY_FAILURE"
            }

        return {
            "success": True,
            "status": "SUCCESS"
        }


    def test_sleep(seconds):

        print(
            f"[TEST MODE] "
            f"Would wait {seconds} seconds"
        )


    result = execute_with_retry(
        operation=failing_operation,
        sleep_function=test_sleep
    )

    print("\nFinal Retry Result")
    print("==================")

    print(result)