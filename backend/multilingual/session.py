from datetime import datetime, timedelta


class SessionManager:
    """
    Manage multilingual customer conversation sessions.

    Rules:
    - 30 minutes inactivity -> session becomes inactive
    - Return within 24 hours -> restore previous session summary
    - Return after 24 hours -> start a new session
    """

    def __init__(
        self,
        inactivity_minutes=30,
        restore_hours=24
    ):
        self.inactivity_minutes = inactivity_minutes
        self.restore_hours = restore_hours

        self.sessions = {}

    # ========================================================
    # CREATE SESSION
    # ========================================================

    def create_session(self, customer_id):
        """
        Create a new session for a customer.
        """

        now = datetime.now()

        session_id = (
            f"{customer_id}_"
            f"{now.strftime('%Y%m%d%H%M%S%f')}"
        )

        self.sessions[customer_id] = {
            "session_id": session_id,
            "customer_id": customer_id,
            "created_at": now,
            "last_activity": now,
            "active": True,
            "summary": "",
            "unresolved_started_at": None
        }

        return self.sessions[customer_id]

    # ========================================================
    # UPDATE ACTIVITY
    # ========================================================

    def update_activity(self, customer_id):
        """
        Update the customer's latest activity time.
        """

        session = self.sessions.get(customer_id)

        if not session:
            return None

        session["last_activity"] = datetime.now()
        session["active"] = True

        return session

    # ========================================================
    # CHECK SESSION STATUS
    # ========================================================

    def check_session_status(
        self,
        customer_id,
        current_time=None
    ):
        """
        Determine whether the current session is active,
        inactive, restorable, or expired.
        """

        session = self.sessions.get(customer_id)

        if not session:

            return {
                "status": "NEW",
                "session": None
            }

        now = current_time or datetime.now()

        inactivity_limit = timedelta(
            minutes=self.inactivity_minutes
        )

        restore_limit = timedelta(
            hours=self.restore_hours
        )

        inactive_for = (
            now - session["last_activity"]
        )

        session_age = (
            now - session["created_at"]
        )

        # ----------------------------------------------------
        # Active session
        # ----------------------------------------------------

        if inactive_for <= inactivity_limit:

            return {
                "status": "ACTIVE",
                "session": session
            }

        # ----------------------------------------------------
        # Inactive but restorable
        # ----------------------------------------------------

        if session_age <= restore_limit:

            session["active"] = False

            return {
                "status": "RESTORABLE",
                "session": session,
                "message": (
                    "Previous conversation summary "
                    "can be restored."
                )
            }

        # ----------------------------------------------------
        # Expired
        # ----------------------------------------------------

        return {
            "status": "EXPIRED",
            "session": session,
            "message": (
                "Previous session has expired. "
                "A new session is required."
            )
        }

    # ========================================================
    # SET SUMMARY
    # ========================================================

    def set_summary(
        self,
        customer_id,
        summary
    ):
        """
        Store a summary for future restoration.
        """

        session = self.sessions.get(customer_id)

        if not session:
            return False

        session["summary"] = summary

        return True

    # ========================================================
    # RESTORE SESSION
    # ========================================================

    def restore_session(
        self,
        customer_id,
        current_time=None
    ):
        """
        Restore an inactive session when it is still
        within the configured restoration period.
        """

        result = self.check_session_status(
            customer_id,
            current_time=current_time
        )

        if result["status"] != "RESTORABLE":

            return result

        session = result["session"]

        session["active"] = True
        session["last_activity"] = (
            current_time or datetime.now()
        )

        return {
            "status": "RESTORED",
            "session": session,
            "summary": session.get(
                "summary",
                ""
            )
        }
    # ========================================================
    # START NEW SESSION
    # ========================================================

    def start_new_session(self, customer_id):
        """
        Start a completely new session.
        """

        return self.create_session(
            customer_id
        )

    # ========================================================
    # UNRESOLVED NEGATIVE CONVERSATION
    # ========================================================

    def start_unresolved(self, customer_id):
        """
        Start the unresolved timer for a negative conversation.
        Does not reset an existing timer.
        """

        session = self.sessions.get(customer_id)

        if not session:
            return None

        if session.get("unresolved_started_at") is None:
            session["unresolved_started_at"] = datetime.now()

        return session["unresolved_started_at"]


    def clear_unresolved(self, customer_id):
        """
        Clear the unresolved timer when the issue is resolved.
        """

        session = self.sessions.get(customer_id)

        if not session:
            return False

        session["unresolved_started_at"] = None

        return True


    def get_unresolved_minutes(self, customer_id):
        """
        Return how many minutes the conversation has remained unresolved.
        """

        session = self.sessions.get(customer_id)

        if not session:
            return 0

        started_at = session.get("unresolved_started_at")

        if started_at is None:
            return 0

        elapsed = datetime.now() - started_at

        return max(0, int(elapsed.total_seconds() // 60))
# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("MULTILINGUAL SESSION MANAGEMENT TEST")
    print("=" * 60)

    manager = SessionManager(
        inactivity_minutes=30,
        restore_hours=24
    )

    customer_id = "customer_001"

    # --------------------------------------------------------
    # Create session
    # --------------------------------------------------------

    session = manager.create_session(
        customer_id
    )

    print("\n1. New session:")
    print(session)

    # --------------------------------------------------------
    # Active session
    # --------------------------------------------------------

    status = manager.check_session_status(
        customer_id
    )

    print("\n2. Active session:")
    print(status["status"])

    # --------------------------------------------------------
    # Add summary
    # --------------------------------------------------------

    manager.set_summary(
        customer_id,
        "Customer asked about a refund for ORD12345."
    )

    # --------------------------------------------------------
    # Simulate 31 minutes inactivity
    # --------------------------------------------------------

    simulated_time = (
        session["last_activity"]
        + timedelta(minutes=31)
    )

    status = manager.check_session_status(
        customer_id,
        current_time=simulated_time
    )

    print("\n3. After 31 minutes:")
    print(status["status"])

    # --------------------------------------------------------
    # Simulate restoration within 24 hours
    # --------------------------------------------------------

    restored = manager.restore_session(
        customer_id,
        current_time=simulated_time
    )

    print("\n4. Restore session:")
    print(restored["status"])

    print(
        "Summary:",
        restored.get("summary")
    )

    # --------------------------------------------------------
    # Simulate more than 24 hours
    # --------------------------------------------------------

    expired_time = (
        session["created_at"]
        + timedelta(hours=25)
    )

    status = manager.check_session_status(
        customer_id,
        current_time=expired_time
    )

    print("\n5. After 25 hours:")
    print(status["status"])