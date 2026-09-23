import json
from pathlib import Path
from datetime import datetime


# ==========================================
# VERSION HISTORY PATH
# ==========================================

VERSION_FILE = Path(
    "data/knowledge_base/version_history.json"
)


# ==========================================
# LOAD VERSION HISTORY
# ==========================================

def load_version_history():
    """
    Load version history from JSON file.
    """

    if not VERSION_FILE.exists():
        return {}

    try:
        with open(
            VERSION_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except (json.JSONDecodeError, OSError):
        return {}


# ==========================================
# SAVE VERSION HISTORY
# ==========================================

def save_version_history(history):
    """
    Save version history to JSON file.
    """

    VERSION_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        VERSION_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            history,
            file,
            indent=4
        )


# ==========================================
# REGISTER DOCUMENT VERSION
# ==========================================

def register_version(
    filename,
    file_hash,
    metadata,
    file_path
):
    """
    Register a new document version.
    """

    history = load_version_history()

    if filename not in history:

        history[filename] = {
            "current_version": 0,
            "versions": []
        }

    current_version = (
        history[filename]["current_version"]
    )

    new_version = current_version + 1

    version_record = {
        "version": new_version,
        "hash": file_hash,
        "metadata": metadata,
        "file_path": str(file_path),
        "created_at": datetime.now().isoformat()
    }

    history[filename]["versions"].append(
        version_record
    )

    history[filename]["current_version"] = (
        new_version
    )

    save_version_history(history)

    return version_record


# ==========================================
# GET CURRENT VERSION
# ==========================================

def get_current_version(filename):
    """
    Return the current version of a document.
    """

    history = load_version_history()

    if filename not in history:
        return None

    return history[filename]["current_version"]


# ==========================================
# GET VERSION HISTORY
# ==========================================

def get_document_versions(filename):
    """
    Return all stored versions of a document.
    """

    history = load_version_history()

    if filename not in history:
        return []

    return history[filename]["versions"]

# ==========================================
# ROLLBACK DOCUMENT
# ==========================================

def rollback_document(filename, target_version):
    """
    Roll back a document to a previously stored version.
    """

    history = load_version_history()

    if filename not in history:
        return {
            "success": False,
            "message": "Document not found in version history."
        }

    versions = history[filename]["versions"]

    target = None

    for version in versions:

        if version["version"] == target_version:
            target = version
            break

    if target is None:
        return {
            "success": False,
            "message": f"Version {target_version} not found."
        }

    history[filename]["current_version"] = target_version

    save_version_history(history)

    return {
        "success": True,
        "filename": filename,
        "rolled_back_to": target_version,
        "hash": target["hash"],
        "metadata": target["metadata"],
        "file_path": target["file_path"]
    }
# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    print("\nKnowledge Base Versioning")
    print("=========================")

    # Example metadata
    metadata = {
        "Document": "Refund Policy",
        "Version": "1.0",
        "Product": "All Products",
        "Region": "India",
        "Effective Date": "2026-01-01",
        "Expiry Date": "2027-01-01",
        "Access Level": "Public"
    }

    # Example document hash
    example_hash = "example_hash_123"

    version = register_version(
        filename="refund_policy.txt",
        file_hash=example_hash,
        metadata=metadata,
        file_path="data/knowledge_base/incoming/refund_policy.txt"
    )

    print("\nRegistered Version:")
    print(version)

    print(
        "\nCurrent Version:",
        get_current_version("refund_policy.txt")
    )

    print("\nVersion History:")

    for item in get_document_versions(
        "refund_policy.txt"
    ):
        print(item)

    print("\nRollback Test")
    print("=============")

    rollback_result = rollback_document(
        filename="refund_policy.txt",
        target_version=1
    )

    print(rollback_result)

    print(
        "\nCurrent Version After Rollback:",
        get_current_version("refund_policy.txt")
    )