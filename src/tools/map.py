import folium
import structlog
import pandas as pd
from pydantic import BaseModel, Field
import re
from .csv_loading import get_cleaned_address_dataframe
from .clustering import make_balanced_clustering

logger = structlog.get_logger()


class RouteConfig(BaseModel):
    name: str
    color: str | None = None

    # Check if the color is a valid hex color
    if color and not re.match(r"^#([0-9a-fA-F]{6})$", color):
        raise ValueError("Invalid hex color")


class RouteListConfig(BaseModel):
    route_count: int = 1
    routes: list[RouteConfig] = Field(default_factory=list)
    random_state: int = 42
    clustering_method: str = "kmeans"
    seed: int = 42


def generate_map(
    city_name: str,
    department_code: int,
    routes_config: RouteListConfig = RouteListConfig(),
):
    """
    Generate a map for the specified city.

    Args:
        city_name: City name
        department_code: Department code
        routes_config: Route configuration data
    Returns:
        tuple[folium.Map, dict]: The generated map and cluster statistics
    """
    logger.info("Generating map", city_name=city_name, department_code=department_code)
    if len(routes_config.routes) < routes_config.route_count:
        raise ValueError("Route configuration does not match the requested route count")

    # Get and clean address dataframe for the city
    try:
        df = get_cleaned_address_dataframe(department_code, city_name)
    except Exception as e:
        logger.error("Error getting cleaned address dataframe", error=str(e))
        raise ValueError("Error getting cleaned address dataframe") from e
    center_lat = df["lat"].mean()
    center_lon = df["lon"].mean()
    logger.info("Center of the map", center_lat=center_lat, center_lon=center_lon)
    m = folium.Map(location=[center_lat, center_lon], zoom_start=14)

    # Generate the routes
    if routes_config.route_count > 1:
        clustering_method = routes_config.clustering_method

        if clustering_method == "kmeans":
            df, cluster_stats = make_balanced_clustering(
                df, None, routes_config.route_count, routes_config.seed
            )
        elif clustering_method == "balanced_length":
            df, cluster_stats = make_balanced_clustering(
                df, "length", routes_config.route_count, routes_config.seed
            )
        elif clustering_method == "balanced_count":
            df, cluster_stats = make_balanced_clustering(
                df, "count", routes_config.route_count, routes_config.seed
            )
        else:
            logger.error("Invalid method", method=clustering_method)
            raise ValueError("Invalid method")
    else:
        df["cluster"] = 0
        cluster_stats = pd.DataFrame({"count": [len(df)], "length": None})
    for i in range(routes_config.route_count):
        cluster_stats.loc[i, "color"] = routes_config.routes[i].color
        cluster_stats.loc[i, "name"] = routes_config.routes[i].name

    for _, row in df.iterrows():
        address = row["address"]
        route_index = row["cluster"]
        route_name = routes_config.routes[route_index].name
        color = cluster_stats["color"][route_index]
        popup = folium.Popup(
            f"<b>Address:</b> {address}<br><b>Route:</b> {route_name}", max_width=300
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
    return m, cluster_stats.to_dict()


if __name__ == "__main__":
    routes_config = RouteListConfig(
        route_count=5,
        routes=[
            RouteConfig(name="Route 1", color="#ffff14"),
            RouteConfig(name="Route 2", color="#6e750e"),
            RouteConfig(name="Route 3", color="#ff028d"),
            RouteConfig(name="Route 4", color="#000000"),
            RouteConfig(name="Route 5", color="#4d4d4d"),
            RouteConfig(name="Route 6", color="#ffff14"),
            RouteConfig(name="Route 7", color="#6e750e"),
            RouteConfig(name="Route 8", color="#ff028d"),
            RouteConfig(name="Route 9", color="#000000"),
            RouteConfig(name="Route 10", color="#4d4d4d"),
            RouteConfig(name="Route 1", color="#ffff14"),
            RouteConfig(name="Route 2", color="#6e750e"),
            RouteConfig(name="Route 3", color="#ff028d"),
            RouteConfig(name="Route 4", color="#000000"),
            RouteConfig(name="Route 5", color="#4d4d4d"),
            RouteConfig(name="Route 6", color="#ffff14"),
            RouteConfig(name="Route 7", color="#6e750e"),
            RouteConfig(name="Route 8", color="#ff028d"),
            RouteConfig(name="Route 9", color="#000000"),
            RouteConfig(name="Route 10", color="#4d4d4d"),
        ],
        clustering_method="balanced_count",
    )
    m, cluster_stats = generate_map("Assas", 34, routes_config)
    m.save("map.html")
    print(cluster_stats)
