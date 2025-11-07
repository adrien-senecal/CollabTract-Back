import requests
import pandas as pd
import pathlib
import structlog

from .validation import validate_department_code, check_folder_path

logger = structlog.get_logger()


def download_address_dataset(
    department_code: str | int, output_folder: pathlib.Path | None = None
) -> pathlib.Path:
    logger.info(
        "Downloading local address dataset",
        department_code=department_code,
        output_folder=output_folder,
    )

    department_code = validate_department_code(department_code)
    output_folder = check_folder_path(output_folder)

    # Define the file path
    filename = f"adresses-{department_code}.csv.gz"
    filepath = output_folder / filename

    # Download the file
    url = rf"https://adresse.data.gouv.fr/data/ban/adresses/latest/csv/adresses-{department_code}.csv.gz"
    response = requests.get(url)
    response.raise_for_status()

    # Save the file
    with open(filepath, "wb") as f:
        f.write(response.content)

    logger.info("File saved", filepath=filepath)
    return filepath


def get_address_dataframe(
    department_code: str | int, folder_path: pathlib.Path | None = None
) -> pd.DataFrame:
    """
    Get address data for a specific department.

    Args:
        department_code: Department code (e.g., "34", "2A", "971")
        folder_path: Optional path to the folder where CSV files are stored

    Returns:
        pd.DataFrame: Address data for the department
    """
    logger.info("Loading address dataframe", department_code=department_code)
    department_code = validate_department_code(department_code)
    filename = f"adresses-{department_code}.csv.gz"
    folder_path = check_folder_path(folder_path)
    filepath = folder_path / filename

    if not filepath.exists():
        logger.info("File does not exist, loading from internet", filepath=filepath)
        try:
            download_address_dataset(department_code, folder_path)
        except Exception as e:
            logger.error(
                "Failed to load address data from internet",
                error=str(e),
                department_code=department_code,
            )
            return pd.DataFrame()  # Return empty DataFrame on error
    else:
        logger.info("File exists, loading from local", filepath=filepath.name)

    try:
        df = pd.read_csv(filepath, compression="gzip", delimiter=";")
        logger.info(
            "Successfully loaded address data",
            rows=len(df),
            department_code=department_code,
        )
        return df.rename(
            columns={
                "numero": "street_number",
                "rep": "street_suffix",
                "nom_voie": "street_name",
                "code_postal": "postal_code",
                "nom_commune": "city_name",
            }
        )
    except Exception as e:
        logger.error(
            "Failed to read address data file", error=str(e), filepath=filepath
        )
        return pd.DataFrame()  # Return empty DataFrame on error
