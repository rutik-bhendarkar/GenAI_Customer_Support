from collections import deque


class ConversationContext:
    """
    Maintains conversation history for a customer session.

    The system keeps the most recent 10 messages by default.
    """

    def __init__(self, max_messages=10):
        self.max_messages = max_messages

        self.messages = deque(
            maxlen=max_messages
        )

    def add_message(self, role, content):
        """
        Add a message to the conversation history.
        """

        self.messages.append({
            "role": role,
            "content": content
        })

    def get_history(self):
        """
        Return the current conversation history.
        """

        return list(self.messages)

    def get_message_count(self):
        """
        Return the number of stored messages.
        """

        return len(self.messages)

    def get_recent_messages(self, count=5):
        """
        Return the most recent messages.
        """

        return list(self.messages)[-count:]

    def clear(self):
        """
        Clear the conversation history.
        """

        self.messages.clear()


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("MULTILINGUAL CONVERSATION CONTEXT TEST")
    print("=" * 60)

    context = ConversationContext(
        max_messages=10
    )

    # Add 12 messages to verify that only
    # the latest 10 are retained.

    for i in range(1, 13):

        context.add_message(
            role="customer",
            content=f"Test message {i}"
        )

    print("\nStored messages:")
    for message in context.get_history():
        print(message)

    print(
        "\nMessage count:",
        context.get_message_count()
    )

    print("\nMost recent 3 messages:")
    print(
        context.get_recent_messages(3)
    )