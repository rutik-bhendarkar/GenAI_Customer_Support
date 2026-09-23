from pathlib import Path
from datetime import datetime, timedelta


PROCESSED_DIR = Path("data/uploads/processed")
REJECTED_DIR = Path("data/uploads/rejected")


def cleanup_directory(directory, retention_hours=24):
    """
    Delete files older than the configured retention period.
    """

    directory = Path(directory)

    if not directory.exists():
        return []

    cutoff_time = datetime.now() - timedelta(
        hours=retention_hours
    )

    deleted_files = []

    for file_path in directory.iterdir():

        if not file_path.is_file():
            continue

        modified_time = datetime.fromtimestamp(
            file_path.stat().st_mtime
        )

        if modified_time < cutoff_time:

            file_path.unlink()

            deleted_files.append(
                str(file_path)
            )

    return deleted_files


def cleanup_uploads(retention_hours=24):
    """
    Clean both processed and rejected uploads.
    """

    deleted_files = []

    deleted_files.extend(
        cleanup_directory(
            PROCESSED_DIR,
            retention_hours
        )
    )

    deleted_files.extend(
        cleanup_directory(
            REJECTED_DIR,
            retention_hours
        )
    )

    return deleted_files


if __name__ == "__main__":

    print("=" * 60)
    print("MULTIMODAL UPLOAD RETENTION CLEANUP")
    print("=" * 60)

    deleted = cleanup_uploads(
        retention_hours=24
    )

    print("\nDeleted files:")

    if deleted:
        for file_path in deleted:
            print("-", file_path)
    else:
        print("No expired files found.")