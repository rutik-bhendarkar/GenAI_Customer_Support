from pathlib import Path
from datetime import datetime, time
import shutil

from backend.knowledge_base.scanner import (
    scan_documents,
    detect_duplicates,
    detect_new_or_modified
)

from backend.knowledge_base.validator import (
    validate_document,
    quality_check,
    quarantine_document
)

from backend.knowledge_base.versioning import (
    load_version_history,
    register_version
)

from backend.knowledge_base.monitoring import (
    KnowledgeBaseMonitor
)

from backend.knowledge_base.retry import (
    execute_with_retry
)

from backend.knowledge_base.rollback import (
    backup_active_document,
    rollback_document
)


# ==========================================
# KNOWLEDGE BASE PATHS
# ==========================================

INCOMING_FOLDER = Path(
    "data/knowledge_base/incoming"
)

ACTIVE_FOLDER = Path(
    "data/knowledge_base/active"
)

ARCHIVE_FOLDER = Path(
    "data/knowledge_base/archive"
)


# ==========================================
# MAINTENANCE WINDOW
# ==========================================

MAINTENANCE_START = time(2, 0)
MAINTENANCE_END = time(4, 0)


# ==========================================
# ROLLBACK WINDOW
# ==========================================

ROLLBACK_WINDOW_MINUTES = 5


# ==========================================
# CHECK MAINTENANCE WINDOW
# ==========================================

def is_maintenance_window(current_time=None):

    if current_time is None:
        current_time = datetime.now().time()

    if MAINTENANCE_START <= MAINTENANCE_END:

        return (
            MAINTENANCE_START
            <= current_time
            <= MAINTENANCE_END
        )

    return (
        current_time >= MAINTENANCE_START
        or current_time <= MAINTENANCE_END
    )


# ==========================================
# ACTIVATE DOCUMENT
# ==========================================

def activate_document(
    filename,
    current_time=None
):

    source = INCOMING_FOLDER / filename
    destination = ACTIVE_FOLDER / filename

    ACTIVE_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )

    ARCHIVE_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )

    if not source.exists():

        return {
            "success": False,
            "status": "NOT_FOUND"
        }

    if not is_maintenance_window(
        current_time
    ):

        return {
            "success": False,
            "status":
                "WAITING_FOR_MAINTENANCE_WINDOW"
        }

    # Archive existing active version
    if destination.exists():

        archive_name = (
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_"
            f"{filename}"
        )

        archive_path = (
            ARCHIVE_FOLDER / archive_name
        )

        shutil.copy2(
            destination,
            archive_path
        )

    # Activate new document
    shutil.copy2(
        source,
        destination
    )

    return {
        "success": True,
        "status": "ACTIVATED",
        "filename": filename,
        "active_path": str(destination),
        "activated_at":
            datetime.now().isoformat()
    }


# ==========================================
# COMPLETE KNOWLEDGE BASE PIPELINE
# ==========================================

def process_knowledge_base(
    current_time=None
):

    monitor = KnowledgeBaseMonitor()

    print("\n")
    print("=" * 50)
    print("KNOWLEDGE BASE PIPELINE")
    print("=" * 50)

    # --------------------------------------
    # 1. SCAN
    # --------------------------------------

    documents = scan_documents()

    print("\n1. DOCUMENT SCANNING")
    print("--------------------")

    print(
        f"Documents found: {len(documents)}"
    )

    if not documents:

        return {
            "status": "NO_DOCUMENTS",
            "documents": []
        }

    # --------------------------------------
    # 2. DUPLICATE DETECTION
    # --------------------------------------

    print("\n2. DUPLICATE DETECTION")
    print("----------------------")

    duplicates = detect_duplicates(
        documents
    )

    duplicate_files = {
        item["duplicate_file"]
        for item in duplicates
    }

    print(
        f"Duplicates found: {len(duplicates)}"
    )

    for duplicate in duplicates:

        print(
            f"Duplicate: "
            f"{duplicate['duplicate_file']} "
            f"-> "
            f"{duplicate['original_file']}"
        )

    # --------------------------------------
    # 3. NEW / MODIFIED DETECTION
    # --------------------------------------

    print("\n3. NEW / MODIFIED DETECTION")
    print("---------------------------")

    history = load_version_history()

    previous_documents = {}

    for filename, data in history.items():

        versions = data.get(
            "versions",
            []
        )

        if versions:

            previous_documents[filename] = (
                versions[-1]["hash"]
            )

    changes = detect_new_or_modified(
        documents,
        previous_documents
    )

    print(
        f"New/modified documents: "
        f"{len(changes)}"
    )

    changed_files = {
        item["filename"]
        for item in changes
    }

    # --------------------------------------
    # 4. PROCESS DOCUMENTS
    # --------------------------------------

    results = []

    for document in documents:

        filename = document["filename"]

        # ----------------------------------
        # SKIP DUPLICATES
        # ----------------------------------

        if filename in duplicate_files:

            print(
                f"\nSKIPPED DUPLICATE: {filename}"
            )

            results.append({
                "filename": filename,
                "status": "DUPLICATE_SKIPPED"
            })

            continue

        # ----------------------------------
        # SKIP UNCHANGED
        # ----------------------------------

        if (
            filename not in changed_files
            and filename in previous_documents
        ):

            print(
                f"\nSKIPPED UNCHANGED: {filename}"
            )

            results.append({
                "filename": filename,
                "status": "UNCHANGED"
            })

            continue

        file_path = Path(
            document["path"]
        )

        processing_start = datetime.now()

        # ----------------------------------
        # 5. METADATA VALIDATION
        # ----------------------------------

        validation = validate_document(
            file_path
        )

        if not validation["valid"]:

            print(
                f"\nINVALID: {filename}"
            )

            quarantine_result = (
                quarantine_document(
                    file_path
                )
            )

            monitor.record_quarantine()

            results.append({
                "filename": filename,
                "status": "QUARANTINED",
                "reason":
                    validation["missing_fields"]
            })

            monitor.record_processing(
                (
                    datetime.now()
                    - processing_start
                ).total_seconds() * 1000,
                success=False
            )

            continue

        # ----------------------------------
        # 6. QUALITY CHECK
        # ----------------------------------

        quality = quality_check(
            file_path
        )

        if not quality["passed"]:

            print(
                f"\nQUALITY FAILED: {filename}"
            )

            quarantine_result = (
                quarantine_document(
                    file_path
                )
            )

            monitor.record_quarantine()

            results.append({
                "filename": filename,
                "status": "QUARANTINED",
                "reason":
                    quality["issues"]
            })

            monitor.record_processing(
                (
                    datetime.now()
                    - processing_start
                ).total_seconds() * 1000,
                success=False
            )

            continue

        # ----------------------------------
        # RECORD QUALITY SCORE IF AVAILABLE
        # ----------------------------------

        if "score" in quality:

            monitor.record_quality(
                quality["score"]
            )

        # ----------------------------------
        # 7. REGISTER VERSION
        # ----------------------------------

        version = register_version(
            filename=filename,
            file_hash=document["hash"],
            metadata=validation["metadata"],
            file_path=file_path
        )

        print(
            f"\nVALID: {filename}"
        )

        print(
            f"Version: {version['version']}"
        )

        # ----------------------------------
        # 8. CREATE ROLLBACK BACKUP
        # ----------------------------------

        backup_result = (
            backup_active_document(
                filename
            )
        )

        activation_backup = None

        if backup_result["success"]:

            activation_backup = (
                backup_result["backup_path"]
            )

            print(
                f"Rollback backup created: "
                f"{activation_backup}"
            )

        else:

            print(
                f"No previous active version "
                f"to back up: "
                f"{backup_result['status']}"
            )

        # ----------------------------------
        # 9. MAINTENANCE WINDOW + RETRIES
        # ----------------------------------

        def activation_operation():

            return activate_document(
                filename,
                current_time=current_time
            )

        retry_result = execute_with_retry(
            operation=activation_operation
        )

        activation = retry_result["result"]

        # ----------------------------------
        # ACTIVATION RESULT
        # ----------------------------------

        if retry_result["success"]:

            monitor.record_activation(
                success=True
            )

            status = "ACTIVATED"

            print(
                f"ACTIVATED: {filename}"
            )

        else:

            monitor.record_activation(
                success=False
            )

            status = retry_result.get(
                "status",
                activation.get(
                    "status",
                    "FAILED"
                )
            )

            print(
                f"ACTIVATION FAILED: "
                f"{filename}"
            )

        # ----------------------------------
        # 10. PROCESSING METRICS
        # ----------------------------------

        processing_time = (
            datetime.now()
            - processing_start
        ).total_seconds() * 1000

        monitor.record_processing(
            processing_time_ms=processing_time,
            success=activation["success"]
        )

        # ----------------------------------
        # STORE INITIAL RESULT
        # ----------------------------------

        result_entry = {
            "filename": filename,
            "status": status,
            "version": version["version"],
            "processing_time_ms":
                round(processing_time, 2)
        }

        # ----------------------------------
        # 11. POST-DEPLOYMENT HEALTH CHECK
        # ----------------------------------

        health = monitor.health_check()

        print(
            "\nPOST-DEPLOYMENT HEALTH CHECK"
        )
        print(
            "----------------------------"
        )

        print(
            "Status:",
            health["status"]
        )

        print(
            "Failure Rate:",
            health["failure_rate_percent"],
            "%"
        )

        # ----------------------------------
        # 12. AUTOMATIC ROLLBACK
        # ----------------------------------

        if (
            activation["success"]
            and not health["healthy"]
            and activation_backup
        ):

            print(
                f"\nHEALTH CHECK FAILED."
            )

            print(
                f"Rollback window: "
                f"{ROLLBACK_WINDOW_MINUTES} minutes"
            )

            rollback_result = rollback_document(
                filename,
                activation_backup
            )

            if rollback_result["success"]:

                status = "ROLLED_BACK"

                monitor.record_escalation()

                result_entry["status"] = (
                    "ROLLED_BACK"
                )

                result_entry[
                    "rollback_reason"
                ] = (
                    "POST_DEPLOYMENT_HEALTH_CHECK_FAILED"
                )

                result_entry[
                    "rollback_window_minutes"
                ] = ROLLBACK_WINDOW_MINUTES

                print(
                    "Automatic rollback completed."
                )

            else:

                status = "ROLLBACK_FAILED"

                monitor.record_escalation()

                result_entry["status"] = (
                    "ROLLBACK_FAILED"
                )

                result_entry[
                    "rollback_reason"
                ] = (
                    "POST_DEPLOYMENT_HEALTH_CHECK_FAILED"
                )

                print(
                    "Automatic rollback FAILED."
                )

        elif activation["success"]:

            print(
                "Deployment health check passed."
            )

        # ----------------------------------
        # 13. FINAL RESULT
        # ----------------------------------

        results.append(
            result_entry
        )

    # --------------------------------------
    # 14. FINAL HEALTH CHECK
    # --------------------------------------

    health = monitor.health_check()

    print("\n4. HEALTH CHECK")
    print("---------------")

    print(
        "Status:",
        health["status"]
    )

    print(
        "Failure Rate:",
        health["failure_rate_percent"],
        "%"
    )

    print(
        "Average Processing Time:",
        health[
            "average_processing_time_ms"
        ],
        "ms"
    )

    # --------------------------------------
    # 15. PIPELINE COMPLETE
    # --------------------------------------

    print("\n5. PIPELINE COMPLETE")
    print("--------------------")

    return {
        "status": "COMPLETED",
        "documents_found": len(documents),
        "duplicates": duplicates,
        "changes": changes,
        "results": results,
        "metrics": monitor.get_metrics(),
        "health": health
    }


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    # Use 03:00 AM for testing because it
    # falls inside our maintenance window.

    result = process_knowledge_base(
        current_time=time(3, 0)
    )

    print("\nFinal Pipeline Result")
    print("=====================")

    for key, value in result.items():

        print(f"\n{key}:")
        print(value)


    if __name__ == "__main__":
        print("Maintenance Window Test")
        print("Current hour:", datetime.now().hour)
        print("Is maintenance window:", is_maintenance_window())


if __name__ == "__main__":
    from datetime import time

    print("Maintenance Window Test")

    print("02:00 ->", is_maintenance_window(time(2, 0)))
    print("03:00 ->", is_maintenance_window(time(3, 0)))
    print("04:00 ->", is_maintenance_window(time(4, 0)))
    print("10:00 ->", is_maintenance_window(time(10, 0)))