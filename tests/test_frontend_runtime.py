"""
Runtime test for the frontend chat interface.

The test runs tests/frontend_harness.js with Node.js. The harness
loads frontend/script.js inside a stubbed DOM, triggers the real
event handlers and checks the complete chat/upload flow (including
XSS escaping and API error handling).

It is skipped when Node.js 20+ is not installed, so the Python test
suite still passes on machines without a JavaScript runtime.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest


TESTS_DIR = Path(__file__).parent

HARNESS = TESTS_DIR / "frontend_harness.js"

FRONTEND_SCRIPT = Path("frontend/script.js")


def node_executable():
    """Return the Node.js executable, or None when it is missing."""

    return shutil.which("node")


def node_major_version(node_executable_path):
    """Return the major version of the installed Node.js runtime."""

    try:

        completed = subprocess.run(
            [node_executable_path, "--version"],
            capture_output=True,
            text=True,
            timeout=30
        )

    except (OSError, subprocess.SubprocessError):

        return None

    match = re.search(r"v(\d+)", completed.stdout)

    return int(match.group(1)) if match else None


NODE = node_executable()

NODE_SUPPORTED = (
    NODE is not None
    and node_major_version(NODE) is not None
    and node_major_version(NODE) >= 20
)


requires_node = pytest.mark.skipif(
    not NODE_SUPPORTED,
    reason="Node.js 20 or newer is required for the frontend runtime test."
)


@requires_node
def test_frontend_chat_and_upload_flow():

    assert HARNESS.exists(), "tests/frontend_harness.js is missing."

    assert FRONTEND_SCRIPT.exists(), "frontend/script.js is missing."

    completed = subprocess.run(
        [NODE, str(HARNESS), str(FRONTEND_SCRIPT)],
        capture_output=True,
        text=True,
        timeout=120
    )

    output = completed.stdout + completed.stderr

    assert "[FAIL]" not in output, output

    assert "FRONTEND HARNESS: ALL CHECKS PASSED" in output, output

    assert completed.returncode == 0, output