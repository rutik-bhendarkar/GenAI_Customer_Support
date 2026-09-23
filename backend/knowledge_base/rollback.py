from pathlib import Path
from datetime import datetime
import shutil


# ==========================================
# KNOWLEDGE BASE PATHS
# ==========================================

ACTIVE_FOLDER = Path(
    "data/knowledge_base/active"
)

ARCHIVE_FOLDER = Path(
    "data/knowledge_base/archive"
)


# ==========================================
# BACKUP CURRENT ACTIVE DOCUMENT
# ==========================================

def backup_active_document(filename):

    active_path = ACTIVE_FOLDER / filename

    if not active_path.exists():
        return {
            "success": False,
            "status": "NO_ACTIVE_VERSION"
        }

    ARCHIVE_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )

    backup_name = (
        f"rollback_backup_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_"
        f"{filename}"
    )

    backup_path = ARCHIVE_FOLDER / backup_name

    shutil.copy2(
        active_path,
        backup_path
    )

    return {
        "success": True,
        "status": "BACKUP_CREATED",
        "backup_path": str(backup_path),
        "filename": filename
    }


# ==========================================
# ROLLBACK DOCUMENT
# ==========================================

def rollback_document(
    filename,
    backup_path
):

    active_path = ACTIVE_FOLDER / filename
    backup_path = Path(backup_path)

    if not backup_path.exists():
        return {
            "success": False,
            "status": "BACKUP_NOT_FOUND"
        }

    ACTIVE_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )

    shutil.copy2(
        backup_path,
        active_path
    )

    return {
        "success": True,
        "status": "ROLLED_BACK",
        "filename": filename,
        "restored_from": str(backup_path),
        "rolled_back_at": datetime.now().isoformat()
    }


# ==========================================
# DEPLOYMENT BACKUP
# ==========================================

def deployment_backup(filename):

    return backup_active_document(filename)


# ==========================================
# AUTOMATIC ROLLBACK
# ==========================================

def automatic_rollback(
    filename,
    backup_path,
    health_check_result
):
    """
    Roll back a newly deployed document when
    the post-deployment health check fails.
    """

    if health_check_result.get("healthy", False):

        return {
            "success": True,
            "status": "NO_ROLLBACK_REQUIRED",
            "filename": filename
        }

    rollback_result = rollback_document(
        filename,
        backup_path
    )

    if rollback_result["success"]:

        return {
            "success": True,
            "status": "AUTOMATIC_ROLLBACK_COMPLETED",
            "filename": filename,
            "reason": "POST_DEPLOYMENT_HEALTH_CHECK_FAILED",
            "rollback": rollback_result
        }

    return {
        "success": False,
        "status": "ROLLBACK_FAILED",
        "filename": filename,
        "reason": "POST_DEPLOYMENT_HEALTH_CHECK_FAILED",
        "rollback": rollback_result
    }


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    print("=" * 50)
    print("AUTOMATIC ROLLBACK TEST")
    print("=" * 50)

    test_filename = "refund_policy.txt"

    # Step 1: Backup current active version
    backup = deployment_backup(
        test_filename
    )

    print("\n1. Deployment Backup")
    print(backup)

    if backup["success"]:

        # Simulate failed health check
        failed_health = {
            "healthy": False,
            "status": "UNHEALTHY",
            "failure_rate_percent": 25
        }

        print("\n2. Simulated Health Check")
        print(failed_health)

        # Step 2: Automatic rollback
        rollback = automatic_rollback(
            filename=test_filename,
            backup_path=backup["backup_path"],
            health_check_result=failed_health
        )

        print("\n3. Automatic Rollback")
        print(rollback)

    print("\nAutomatic rollback test completed.")