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


def format_address(row: pd.Series) -> str:
    """
    Constructs a standardized address string from a DataFrame row.

    Args:
        row: A row from the city DataFrame.

    Returns:
        Formatted address string.
    """
    # Extract components
    street_number = (
        str(int(row["street_number"])) if pd.notna(row["street_number"]) else ""
    )
    street_suffix = f" {row['street_suffix']}" if pd.notna(row["street_suffix"]) else ""
    street_name = row["street_name"] if pd.notna(row["street_name"]) else ""
    postal_code = str(int(row["postal_code"])) if pd.notna(row["postal_code"]) else ""
    city_label = row["city_name"] if pd.notna(row["city_name"]) else ""

    # Build address parts
    address_parts = []
    if street_number:
        address_parts.append(street_number + street_suffix)
    if street_name:
        address_parts.append(street_name)

    # Combine into full address
    address_line = ", ".join(address_parts)
    full_address = f"{address_line}, {postal_code} {city_label}".strip(", ")

    return full_address


def get_cleaned_address_dataframe(
    department_code: str | int, city_name: str, folder_path: pathlib.Path | None = None
) -> pd.DataFrame:
    """
    Get and clean address data for a specific city in a department.

    Args:
        department_code: Department code (e.g., "34", "2A", "971")
        city_name: Name of the city to filter by
        folder_path: Optional path to the folder where CSV files are stored

    Returns:
        Cleaned DataFrame with address data for the specified city

    Raises:
        ValueError: If department code is invalid, city is not found, or required columns are missing
    """
    logger.info(
        "Cleaning address dataframe",
        department_code=department_code,
        city_name=city_name,
    )

    # Convert department code to int (validation happens in get_address_dataframe)
    try:
        department_code = int(department_code)
    except (ValueError, TypeError):
        logger.error(
            "Department code must be an integer", department_code=department_code
        )
        raise ValueError("Department code must be an integer")

    # Get address dataframe for the department
    df = get_address_dataframe(department_code, folder_path)

    # Filter by city name
    df = df[df["city_name"] == city_name]
    if df.empty:
        logger.error(
            "City not found in the department",
            city_name=city_name,
            department_code=department_code,
        )
        raise ValueError("City not found in the department")

    # Select required columns
    try:
        df = df[
            [
                "street_number",
                "street_suffix",
                "street_name",
                "postal_code",
                "city_name",
                "lat",
                "lon",
            ]
        ]
    except KeyError as e:
        logger.error("Columns not found in the dataframe", error=str(e))
        raise ValueError("Columns not found in the dataframe") from e

    # Add formatted address column
    df["address"] = df.apply(format_address, axis=1)

    logger.info(
        "Successfully cleaned address dataframe",
        rows=len(df),
        city_name=city_name,
        department_code=department_code,
    )

    return df
