from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from uvicorn import run

import time
from datetime import datetime, timezone
import structlog

from .tools.get_city import get_city_by_name, get_cities_by_postal_code
from .tools.map import generate_map, RouteListConfig, RouteConfig
from .tools.color_code import generate_distinct_colors
from . import __version__
from .tools.health import (
    check_database_connection,
    HealthResponse,
)
from .tools.clustering import process_cluster_request
from .tools.route_types import MapRequest


logger = structlog.get_logger()

app = FastAPI()

# Track application start time for uptime calculation
app_start_time = time.time()

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint to verify API and dependencies status.

    Returns:
        HealthResponse: Comprehensive health status including:
        - Overall status (healthy/unhealthy)
        - Timestamp
        - Application version
        - Uptime in seconds
        - Individual component checks
    """
    try:
        # Perform all health checks
        database_check = check_database_connection()

        # Determine overall status
        all_checks = [database_check]
        overall_status = (
            "healthy"
            if all(check["status"] == "healthy" for check in all_checks)
            else "unhealthy"
        )

        # Calculate uptime
        uptime = time.time() - app_start_time

        if overall_status == "unhealthy":
            logger.error("Health check failed", checks=all_checks)
            raise HTTPException(
                status_code=503, detail=f"Health check failed: {all_checks}"
            )

        return HealthResponse(
            status=overall_status,
            timestamp=datetime.now(timezone.utc).isoformat() + "Z",
            version=__version__,
            uptime=round(uptime, 2),
            checks={
                "database": database_check,
            },
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error("Unexpected error in health check", error=str(e))
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get("/get_city")
async def get_city(city: str = None, postal_code: str = None):
    """
    Get city information by name or postal code.

    Args:
        city: City name to search for
        postal_code: Postal code to search for

    Returns:
        JSON response with city information containing standard_name and department_code
    """
    try:
        if city:
            # Search by city name
            cities = get_city_by_name(city)
            return JSONResponse({"type": "city_name", "input": city, "results": cities})
        elif postal_code:
            # Search by postal code
            cities = get_cities_by_postal_code(postal_code)
            return JSONResponse(
                {"type": "postal_code", "input": postal_code, "results": cities}
            )
        else:
            return JSONResponse(
                {"error": "Either 'city' or 'postal_code' parameter is required"},
                status_code=400,
            )
    except Exception as e:
        logger.error("Error in get_city endpoint", error=str(e))
        return JSONResponse({"error": f"An error occurred: {str(e)}"}, status_code=500)


@app.post("/map", response_class=JSONResponse)
async def get_city_map_html(request: MapRequest):
    """
    Generate and return HTML for a city map with clustering and cluster statistics.

    Args:
        request: MapRequest object containing the parameters.
            - city_name: Name of the city.
            - department_code: Department code (as string, converted to int).
            - cluster_count: Number of clusters (must be > 0).
            - clustering_method: Method used for clustering (e.g., "kmeans").
            - cluster_colors: List of hex colors for clusters (e.g., ["#ff0000", "#00ff00"]).

    Returns:
        JSONResponse: Raw HTML of the Folium map for embedding and cluster statistics
    """
    try:

        if (
            not request.cluster_colors
            or len(request.cluster_colors) < request.cluster_count
        ):
            # cluster_colors = make_color_code(request.cluster_count)
            cluster_colors = generate_distinct_colors(request.cluster_count)
        else:
            cluster_colors = request.cluster_colors

        # Create RouteConfig instances dynamically from cluster_colors
        routes_config = RouteListConfig(
            route_count=request.cluster_count,
            routes=[
                RouteConfig(name=f"Cluster {i+1}", color=color)
                for i, color in enumerate(cluster_colors[: request.cluster_count])
            ],
            clustering_method=request.clustering_method,
            seed=request.seed,
        )

        # Generate the map
        folium_map, cluster_stats = generate_map(
            city_name=request.city_name,
            department_code=request.department_code,
            routes_config=routes_config,
        )

        # Return raw HTML (without template)
        map_html = folium_map._repr_html_()
        return JSONResponse(
            content={
                "map_html": map_html,
                "cluster_stats": cluster_stats,
            },
            status_code=200,
        )

    except Exception as e:
        logger.error("Error generating map", error=str(e))
        return JSONResponse(
            {"error": f"Failed to generate map: {str(e)}"},
            status_code=500,
        )


@app.post("/cluster")
async def get_cluster(request: MapRequest):
    """
    Generate clusters for a city and return the dataframe with cluster assignments.

    Args:
        request: MapRequest object containing the parameters.

    Returns:
        JSONResponse: Dataframe with cluster assignments and cluster statistics
    """
    return await process_cluster_request(request)


if __name__ == "__main__":
    run(app, host="0.0.0.0", port=8000)
