import folium
import structlog
import pandas as pd
from pydantic import BaseModel
import re
from .csv_loading import get_df_adresse_locale
from .clustering import make_balanced_clustering

logger = structlog.get_logger()


class CircuitParams(BaseModel):
    nom: str
    color: str | None = None

    # Check if the color is a valid hex color
    if color and not re.match(r"^#([0-9a-fA-F]{6})$", color):
        raise ValueError("Invalid hex color")


class ListCircuitsParams(BaseModel):
    nbr_circuits: int = 1
    circuits: list[CircuitParams] = []
    random_state: int = 42
    clustering_method: str = "kmeans"
    seed: int = 42


def build_address(row):
    """
    Constructs a standardized address string from a DataFrame row.

    Args:
        row (pd.Series): A row from the df_ville DataFrame.

    Returns:
        str: Formatted address string.
    """
    # Extract components
    numero = str(int(row["numero"])) if pd.notna(row["numero"]) else ""
    rep = f" {row['rep']}" if pd.notna(row["rep"]) else ""
    nom_voie = row["nom_voie"] if pd.notna(row["nom_voie"]) else ""
    code_postal = str(int(row["code_postal"])) if pd.notna(row["code_postal"]) else ""
    nom_commune = row["nom_commune"] if pd.notna(row["nom_commune"]) else ""

    # Build address parts
    address_parts = []
    if numero:
        address_parts.append(numero + rep)
    if nom_voie:
        address_parts.append(nom_voie)

    # Combine into full address
    address_line = ", ".join(address_parts)
    full_address = f"{address_line}, {code_postal} {nom_commune}".strip(", ")

    return full_address


def generate_map(
    city_name: str,
    dep_code: int,
    list_circuits: ListCircuitsParams = ListCircuitsParams(),
):
    """
    Generate a map for the specified city.

    Args:
        city_name: City name
        dep_code: Department code
        list_circuits: List of circuits
    Returns:
        folium.Map: The generated map
    """
    logger.info("Generating map", city_name=city_name, dep_code=dep_code)
    dep_code = int(dep_code)

    # Use department code if provided, otherwise try to extract from city data
    try:
        if not isinstance(dep_code, int):
            logger.error("Department code must be an integer", dep_code=dep_code)
            raise ValueError("Department code must be an integer")
        df = get_df_adresse_locale(dep_code)
        df = df[df["nom_commune"] == city_name]
        if df.empty:
            logger.error(
                "City not found in the department",
                city_name=city_name,
                dep_code=dep_code,
            )
            raise ValueError("City not found in the department")
    except Exception as e:
        logger.error("Error generating map", error=str(e))
        raise ValueError("Error generating map")

    try:
        df = df[
            ["numero", "rep", "nom_voie", "code_postal", "nom_commune", "lat", "lon"]
        ]
    except KeyError as e:
        logger.error("Error generating map", error=str(e))
        raise ValueError("Columns not found in the dataframe")
    df["address"] = df.apply(build_address, axis=1)
    center_lat = df["lat"].mean()
    center_lon = df["lon"].mean()
    logger.info("Center of the map", center_lat=center_lat, center_lon=center_lon)
    m = folium.Map(location=[center_lat, center_lon], zoom_start=14)

    # Generate the circuits
    if list_circuits.nbr_circuits > 1:
        clustering_method = list_circuits.clustering_method

        if clustering_method == "kmeans":
            df, stats_cluster = make_balanced_clustering(
                df, None, list_circuits.nbr_circuits, list_circuits.seed
            )
        elif clustering_method == "balanced_length":
            df, stats_cluster = make_balanced_clustering(
                df, "length", list_circuits.nbr_circuits, list_circuits.seed
            )
        elif clustering_method == "balanced_count":
            df, stats_cluster = make_balanced_clustering(
                df, "count", list_circuits.nbr_circuits, list_circuits.seed
            )
        else:
            logger.error("Invalid method", method=clustering_method)
            raise ValueError("Invalid method")
    else:
        df["cluster"] = 0
        stats_cluster = pd.DataFrame({"count": [len(df)], "length": None})
    for i in range(list_circuits.nbr_circuits):
        stats_cluster.loc[i, "color"] = list_circuits.circuits[i].color
        stats_cluster.loc[i, "name"] = list_circuits.circuits[i].nom

    for _, row in df.iterrows():
        adresse = row["address"]
        circuit = row["cluster"]
        nom = list_circuits.circuits[circuit].nom
        color = stats_cluster["color"][circuit]
        popup = folium.Popup(
            f"<b>Adresse:</b> {adresse}<br><b>Circuit:</b> {nom}", max_width=300
        )
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=5,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            popup=popup,
        ).add_to(m)
    return m, stats_cluster.to_dict()


if __name__ == "__main__":
    list_circuits = ListCircuitsParams(
        nbr_circuits=3,
        circuits=[
            CircuitParams(nom="Circuit 1", color="#ffff14"),
            CircuitParams(nom="Circuit 2", color="#6e750e"),
            CircuitParams(nom="Circuit 3", color="#ff028d"),
        ],
        clustering_method="balanced_length",
    )
    m, stats_cluster = generate_map("Anduze", 30, list_circuits)
    m.save("map.html")
    print(stats_cluster)
