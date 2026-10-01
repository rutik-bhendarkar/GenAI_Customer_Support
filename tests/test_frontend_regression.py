"""
Static regression checks for the frontend chat interface.

The checks are text-based on purpose: they protect the integration
contract (element IDs, endpoint usage, escaping and error handling)
without requiring a browser or a JavaScript runtime inside pytest.

They must be re-run after any frontend change so that the previous
"Chat messages container not found." problem and any XSS regression
cannot come back.
"""

import re
from pathlib import Path

import pytest


FRONTEND_DIR = Path("frontend")

INDEX_HTML = FRONTEND_DIR / "index.html"
SCRIPT_JS = FRONTEND_DIR / "script.js"
STYLE_CSS = FRONTEND_DIR / "style.css"


@pytest.fixture(scope="module")
def index_html():
    """Return the HTML of the chat page."""

    assert INDEX_HTML.exists(), "frontend/index.html is missing."

    return INDEX_HTML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def script_js():
    """Return the JavaScript of the chat page."""

    assert SCRIPT_JS.exists(), "frontend/script.js is missing."

    return SCRIPT_JS.read_text(encoding="utf-8")


def function_body(source, function_name):
    """
    Return the body of a top-level function of script.js.

    The project writes closing braces in column zero, so the first
    "\\n}" after the definition ends the function.
    """

    start = source.index(f"function {function_name}(")

    end = source.index("\n}", start)

    return source[start:end]


# ============================================================
# REQUIRED DOM ELEMENTS
# ============================================================

@pytest.mark.parametrize(
    "element_id",
    [
        "chatBox",
        "messageInput",
        "sendButton",
        "fileInput",
        "uploadButton",
        "customerMessage",
        "resultPanel",
    ]
)
def test_required_element_exists_in_html(index_html, element_id):
    """
    Every element the script looks up must exist in index.html,
    otherwise messages cannot be displayed.
    """

    assert f'id="{element_id}"' in index_html


def test_html_loads_script_and_stylesheet(index_html):

    assert '<script src="script.js"></script>' in index_html

    assert '<link rel="stylesheet" href="style.css">' in index_html

    assert STYLE_CSS.exists(), "frontend/style.css is missing."


def test_script_looks_up_the_chat_container(script_js):
    """
    Regression check for "Chat messages container not found.".

    The container is resolved by ID and a fallback container is
    created when it is missing.
    """

    assert 'getElementById("chatBox")' in script_js

    assert "Chat container was not found. Creating one." in script_js

    assert "if (!chatContainer)" in script_js


# ============================================================
# CHAT FLOW
# ============================================================

def test_script_posts_to_the_chat_endpoint(script_js):

    assert "`${API_BASE_URL}/chat`" in script_js

    assert 'method: "POST"' in script_js

    assert '"Content-Type":' in script_js

    assert "JSON.stringify({" in script_js

    assert "addMessage(" in script_js


def test_script_handles_api_errors(script_js):
    """
    A failing backend must produce a friendly assistant message
    instead of an unhandled exception.
    """

    assert "if (!response.ok)" in script_js

    assert "catch (error)" in script_js

    assert (
        "Sorry, I could not connect to the support server."
        in script_js
    )


@pytest.mark.parametrize(
    "guarded_field,guard",
    [
        ("data.knowledge_base_answer", "if (\n            data.knowledge_base_answer &&"),
        ("data.ticket_information", "if (\n            data.ticket_information &&"),
        ("data.priority", "if (data.priority)"),
        ("data.severity", "if (data.severity)"),
        ("data.escalation", "if (\n            data.escalation &&"),
        ("data.after_hours", "if (\n            data.after_hours &&"),
        (
            "data.ticket_ready",
            "data.ticket_ready === false &&"
        ),
        (
            "data.missing_information",
            "Array.isArray(data.missing_information) &&"
        ),
        (
            "data.knowledge_base_sources",
            "Array.isArray(data.knowledge_base_sources) &&"
        ),
    ]
)
def test_optional_response_fields_are_guarded(script_js, guarded_field, guard):
    """
    Optional response fields must be checked before use so a missing
    field cannot crash the chat.
    """

    assert guarded_field in script_js

    assert guard in script_js


def test_chat_message_display_fields(script_js):
    """
    The assistant bubble shows the order ID, priority, severity, the
    knowledge-base answer and its source document.
    """

    assert "Order ID:" in script_js
    assert "Priority:" in script_js
    assert "Severity:" in script_js
    assert "Source:" in script_js
    assert "Missing information:" in script_js


def test_upload_flow_uses_the_upload_endpoint(script_js):

    assert "`${API_BASE_URL}/upload`" in script_js

    assert 'formData.append(' in script_js

    assert "renderAnalysisPanel(data)" in script_js

    assert "renderAnalysisError(data)" in script_js


# ============================================================
# XSS / SECRET SAFETY
# ============================================================

def test_chat_bubbles_use_text_content(script_js):
    """
    Chat bubbles must be written with textContent so customer or
    backend text can never be interpreted as HTML.
    """

    assert "bubble.textContent" in script_js

    assert "bubble.innerHTML" not in script_js


def test_analysis_panel_escapes_every_value(script_js):
    """
    The two innerHTML panels must escape every dynamic value or use a
    literal ternary. Anything else is an XSS risk.
    """

    for function_name in (
        "renderAnalysisPanel",
        "renderAnalysisError"
    ):

        body = function_body(script_js, function_name)

        assert "panel.innerHTML = html;" in body

        for expression in re.findall(r"\$\{(.+?)\}", body, re.S):

            stripped = expression.strip()

            is_escaped = stripped.startswith("escapeHtml(")

            is_literal_choice = (
                ': "' in stripped or ": '" in stripped
            )

            assert is_escaped or is_literal_choice, (
                f"Unescaped interpolation in {function_name}(): "
                f"{stripped}"
            )


def test_frontend_contains_no_secrets(script_js):
    """
    The frontend must not contain API keys or .env values.
    """

    lowered = script_js.lower()

    for marker in ("api_key", "apikey", "sk-", "bearer ", "openai"):

        assert marker not in lowered

    assert ".env" not in lowered


def test_file_input_keeps_the_allowed_types(index_html):
    """
    The upload input still restricts the selectable file types; the
    authoritative validation stays in the backend.
    """

    assert 'accept=".pdf,.png,.jpg,.jpeg"' in index_html