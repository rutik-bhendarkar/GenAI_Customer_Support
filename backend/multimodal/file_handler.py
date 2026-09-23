from pathlib import Path
import shutil


UPLOAD_PATH = Path("data/uploads")

INCOMING_PATH = UPLOAD_PATH / "incoming"
PROCESSED_PATH = UPLOAD_PATH / "processed"
REJECTED_PATH = UPLOAD_PATH / "rejected"


ALLOWED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".pdf"
}


def create_upload_directories():
    """
    Create required upload directories.
    """

    INCOMING_PATH.mkdir(
        parents=True,
        exist_ok=True
    )

    PROCESSED_PATH.mkdir(
        parents=True,
        exist_ok=True
    )

    REJECTED_PATH.mkdir(
        parents=True,
        exist_ok=True
    )


def is_allowed_file(filename):
    """
    Check whether the uploaded file extension
    is supported.
    """

    extension = Path(
        filename
    ).suffix.lower()

    return extension in ALLOWED_EXTENSIONS


def save_uploaded_file(
    source_path,
    filename
):
    """
    Copy an uploaded file into the incoming
    multimodal processing directory.
    """

    create_upload_directories()

    if not is_allowed_file(filename):

        raise ValueError(
            "Unsupported file type."
        )

    destination = (
        INCOMING_PATH / filename
    )

    shutil.copy2(
        source_path,
        destination
    )

    return destination


def move_to_processed(file_path):
    """
    Move successfully processed file.
    """

    create_upload_directories()

    destination = (
        PROCESSED_PATH /
        Path(file_path).name
    )

    shutil.move(
        str(file_path),
        str(destination)
    )

    return destination


def move_to_rejected(file_path):
    """
    Move rejected file.
    """

    create_upload_directories()

    destination = (
        REJECTED_PATH /
        Path(file_path).name
    )

    shutil.move(
        str(file_path),
        str(destination)
    )

    return destination


if __name__ == "__main__":

    print("=" * 50)
    print("MULTIMODAL FILE HANDLER TEST")
    print("=" * 50)

    create_upload_directories()

    print(
        f"Incoming: {INCOMING_PATH}"
    )

    print(
        f"Processed: {PROCESSED_PATH}"
    )

    print(
        f"Rejected: {REJECTED_PATH}"
    )

    print("\nAllowed extensions:")

    for extension in sorted(
        ALLOWED_EXTENSIONS
    ):
        print(
            f"- {extension}"
        )

    print("\nFile validation:")

    test_files = [
        "invoice.pdf",
        "screenshot.png",
        "product.jpg",
        "document.exe"
    ]

    for filename in test_files:

        print(
            f"{filename}: "
            f"{is_allowed_file(filename)}"
        )