import pathlib

import pandas as pd
from thefuzz import process
import structlog
from ..settings import MUNICIPALITIES_DATA_PATH

logger = structlog.get_logger()


def _load_municipality_data() -> pd.DataFrame:
    df = pd.read_parquet(MUNICIPALITIES_DATA_PATH)
    return df.rename(
        columns={
            "nom_standard": "standard_name",
            "dep_code": "department_code",
            "code_postal": "postal_code",
        }
    )


def get_cities_by_postal_code(
    postal_code: str | int, folder_path: str | pathlib.Path | None = None
) -> list[dict[str, str]]:
    """
    Retrieve the list of cities associated with a given postal code.

    Args:
        postal_code: The postal code to search for (e.g., "34000" or 34000).
        folder_path: Optional path to the folder where the CSV files are stored.
                    If None, uses the default CSV_FOLDER from settings.

    Returns:
        A list of dictionaries containing city names and department codes.
    """
    logger.info("Getting city by postal code", postal_code=postal_code)

    df = _load_municipality_data()
    df = df[df["postal_code"] == str(postal_code)]
    city_department_records: list[dict[str, str]] = []
    for city in df["standard_name"].unique().tolist():
        matches = df[df["standard_name"] == city][
            ["standard_name", "department_code"]
        ]
        city_department_records.extend(matches.to_dict(orient="records"))
    return city_department_records


def filter_cities(cities: list[tuple[str, int]]) -> list[str]:
    # Check if any city has a value of 100
    city_with_100 = [city for city, value in cities if value == 100]

    if city_with_100:
        return city_with_100  # Return only the city/cities with 100
    else:
        # Sort cities by their value in descending order and return up to 5
        sorted_cities = sorted(cities, key=lambda x: x[1], reverse=True)
        return [city for city, value in sorted_cities]


def get_city_by_name(
    city_name: str, folder_path: str | pathlib.Path | None = None
) -> list[dict[str, str]]:
    """
    Retrieve potential city matches for a given name with their department codes.
    """
    logger.info("Getting city by name", city_name=city_name)
    df = _load_municipality_data()
    list_city_name = df["standard_name"].unique().tolist()
    city_names = process.extractBests(city_name, list_city_name, score_cutoff=80)
    city_names = filter_cities(city_names)
    city_department_records = []
    for city in city_names:
        matches = df[df["standard_name"] == city][
            ["standard_name", "department_code"]
        ]
        city_department_records.extend(matches.to_dict(orient="records"))
    return city_department_records


if __name__ == "__main__":
    postal_code_matches = get_cities_by_postal_code("30140")
    print(postal_code_matches)
    city_names = get_city_by_name("Anduza")
    print(city_names)
