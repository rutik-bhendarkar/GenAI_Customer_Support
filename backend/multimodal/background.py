from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from backend.multimodal.processor import process_file


executor = ThreadPoolExecutor(
    max_workers=2
)


def process_file_in_background(
    file_path,
    customer_message=None
):
    """
    Process a multimodal file in the background.

    Returns a Future object so the caller can
    check the result later.
    """

    file_path = Path(file_path)

    future = executor.submit(
        process_file,
        file_path,
        customer_message
    )

    return future


def get_processing_status(future):
    """
    Check whether background processing is complete.
    """

    if future.done():

        try:
            return {
                "status": "COMPLETED",
                "result": future.result()
            }

        except Exception as error:

            return {
                "status": "FAILED",
                "error": str(error)
            }

    return {
        "status": "PROCESSING",
        "message": (
            "File processing is still in progress. "
            "The customer will be notified when processing completes."
        )
    }