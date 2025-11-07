import pathlib

from ..settings import CSV_FOLDER
import structlog

logger = structlog.get_logger()


def check_folder_path(folder_path: pathlib.Path | None) -> pathlib.Path:
    if folder_path is None:
        folder_path = pathlib.Path(CSV_FOLDER)
    elif not isinstance(folder_path, pathlib.Path):
        raise ValueError("folder_path must be a string or a pathlib.Path object")
    folder_path.mkdir(parents=True, exist_ok=True)
    return folder_path


def validate_department_code(department_code: str | int) -> str:
    # Convert to string if it's an integer
    if isinstance(department_code, int):
        department_code = str(department_code)

    # Handle string cases (including 'a' or 'b')
    if isinstance(department_code, str):
        department_code = department_code.upper()  # Transform 'a' or 'b' to 'A' or 'B'

        # Check for valid string formats (2A or 2B)
        if department_code in ["2A", "2B"]:
            return department_code

        # Check for valid integer ranges (01-95 or 971-989)
        if department_code.isdigit():
            num = int(department_code)
            if (1 <= num <= 95) or (971 <= num <= 989):
                return department_code.zfill(
                    2
                )  # Pad with leading zero if needed (e.g., 1 → "01")

    # Return None or raise an error if invalid
    logger.error("Invalid department", department_code=department_code)
    raise ValueError(
        f"Invalid department: {department_code}. Must be 01-95, 971-989, or 2A/2B."
    )
