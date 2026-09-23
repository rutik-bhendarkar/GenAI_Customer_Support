import hashlib
from pathlib import Path


# ==========================================
# KNOWLEDGE BASE PATH
# ==========================================

KB_INCOMING = Path("data/knowledge_base/incoming")


# ==========================================
# CALCULATE FILE HASH
# ==========================================

def calculate_file_hash(file_path: Path) -> str:
    """
    Calculate SHA-256 hash of a file.
    """

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:

        while chunk := file.read(4096):
            sha256.update(chunk)

    return sha256.hexdigest()


# ==========================================
# SCAN KNOWLEDGE BASE
# ==========================================

def scan_documents():
    """
    Scan all files inside the incoming knowledge-base folder.
    """

    documents = []

    if not KB_INCOMING.exists():
        return documents

    for file_path in KB_INCOMING.iterdir():

        if not file_path.is_file():
            continue

        file_hash = calculate_file_hash(file_path)

        documents.append({
            "filename": file_path.name,
            "path": str(file_path),
            "extension": file_path.suffix,
            "size": file_path.stat().st_size,
            "hash": file_hash
        })

    return documents


# ==========================================
# DETECT DUPLICATE DOCUMENTS
# ==========================================

def detect_duplicates(documents):
    """
    Detect duplicate documents using SHA-256 hashes.
    """

    hash_map = {}
    duplicates = []

    for document in documents:

        filename = document["filename"]
        file_hash = document["hash"]

        if file_hash in hash_map:

            duplicates.append({
                "duplicate_file": filename,
                "original_file": hash_map[file_hash],
                "hash": file_hash
            })

        else:

            hash_map[file_hash] = filename

    return duplicates


# ==========================================
# DETECT NEW / MODIFIED DOCUMENTS
# ==========================================

def detect_new_or_modified(documents, previous_documents):
    """
    Detect documents that are new or whose content has changed.

    previous_documents format:

    {
        "filename.txt": "sha256_hash"
    }
    """

    changes = []

    for document in documents:

        filename = document["filename"]
        current_hash = document["hash"]

        # New document
        if filename not in previous_documents:

            changes.append({
                "filename": filename,
                "status": "NEW"
            })

        # Modified document
        elif previous_documents[filename] != current_hash:

            changes.append({
                "filename": filename,
                "status": "MODIFIED"
            })

    return changes


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    print("\nKnowledge Base Documents")
    print("========================")

    documents = scan_documents()

    if not documents:

        print("No documents found.")

    else:

        for document in documents:

            print("\nFilename:", document["filename"])
            print("Extension:", document["extension"])
            print("Size:", document["size"])
            print("Hash:", document["hash"])


    # ======================================
    # DUPLICATE TEST
    # ======================================

    print("\nDuplicate Documents")
    print("===================")

    duplicates = detect_duplicates(documents)

    if duplicates:

        for duplicate in duplicates:

            print("\nDuplicate:", duplicate["duplicate_file"])
            print("Original:", duplicate["original_file"])
            print("Hash:", duplicate["hash"])

    else:

        print("No duplicate documents found.")


    # ======================================
    # NEW / MODIFIED TEST
    # ======================================

    print("\nNew / Modified Documents")
    print("========================")

    # Example previous document database.
    # In the production version this will come
    # from our version/history system.

    previous_documents = {
        "refund_policy.txt":
            "old_hash_example",

        "delivery_policy.txt":
            "ceb6d712411cc0b3c460815851da92c362192633e833ceb516b6e352dba192b6"
    }

    changes = detect_new_or_modified(
        documents,
        previous_documents
    )

    if changes:

        for change in changes:

            print("\nFilename:", change["filename"])
            print("Status:", change["status"])

    else:

        print("No new or modified documents found.")