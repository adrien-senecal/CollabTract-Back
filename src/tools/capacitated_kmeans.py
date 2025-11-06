import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from sklearn.utils.extmath import row_norms
from sklearn.cluster import KMeans
import networkx as nx
import structlog

logger = structlog.get_logger()


def build_gdf(
    df: pd.DataFrame, crs: str = "EPSG:4326", projected_crs: str = "EPSG:2154"
) -> gpd.GeoDataFrame:
    geometry = [Point(lon, lat) for lon, lat in zip(df["lon"], df["lat"])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs=crs)
    gdf_projected = gdf.to_crs(projected_crs)
    return gdf_projected


def dist_matrix(A, B):
    # Euclidean in projected CRS
    # returns (n_points x k) distances
    AA = row_norms(A, squared=True)[:, None]
    BB = row_norms(B, squared=True)[None, :]
    D2 = AA + BB - 2 * A @ B.T
    D2 = np.maximum(D2, 0.0)
    return np.sqrt(D2)


def capacitated_kmeans(
    df: pd.DataFrame,
    k: int,
    weight_col: str = "count",
    x_col: str = None,
    y_col: str = None,
    capacity: float | None = None,
    capacity_tolerance: float = 0.1,
    max_iter: int = 30,
    random_state: int = 42,
):

    gdf = build_gdf(df)
    # 1) Coordinates in meters
    if x_col is None or y_col is None:
        # use geometry directly
        assert gdf.geometry.is_valid.all(), "Invalid geometries found."
        X = np.column_stack([gdf.geometry.x.values, gdf.geometry.y.values])
    else:
        X = gdf[[x_col, y_col]].to_numpy(dtype=float)

    w = gdf[weight_col].to_numpy(dtype=float)
    n = X.shape[0]
    total_w = w.sum()
    if capacity is None:
        capacity = total_w / k
    cap_lo = (1 - capacity_tolerance) * capacity
    cap_hi = (1 + capacity_tolerance) * capacity

    # 2) Initialize centers with k-means++ (ignoring capacities)
    init = KMeans(n_clusters=k, n_init=10, random_state=random_state).fit(X)
    centers = init.cluster_centers_

    labels = np.full(n, -1, dtype=int)

    for it in range(max_iter):
        D = dist_matrix(X, centers)

        # 3) Build min-cost flow for assignment
        G = nx.DiGraph()
        source, sink = "_s", "_t"
        G.add_node(source, demand=-float(total_w))
        G.add_node(sink, demand=float(total_w))

        # Item nodes (supply = weight)
        for i in range(n):
            node_i = f"p_{i}"
            G.add_node(node_i, demand=0)
            # edge from source to item with capacity = weight (we model weight as flow)
            G.add_edge(source, node_i, capacity=w[i], weight=0)

        # Cluster (bin) nodes
        for j in range(k):
            node_j = f"c_{j}"
            G.add_node(node_j, demand=0)
            # capacity band: [cap_lo, cap_hi]
            # Enforce upper bound via capacity to sink, and lower bound via a penalty trick:
            # We’ll connect cluster to sink with two parallel edges:
            # - up to cap_lo at zero cost (ensures we can place at least cap_lo cheaply),
            # - additional (cap_hi - cap_lo) at small cost epsilon to discourage overfill but allow it.
            eps = 0  # set to 0; use >0 if you want to gently discourage overfill
            G.add_edge(node_j, sink, capacity=cap_lo, weight=0)
            if cap_hi > cap_lo:
                G.add_edge(node_j, sink, capacity=cap_hi - cap_lo, weight=eps)

        # Item -> cluster edges with per-unit flow cost = distance
        # To strongly encourage assignment of the entire weight of an item to a single cluster,
        # keep flow integral by scaling weights to integers if needed.
        # Here we assume weights are integers (counts) or scale them.
        scale = 1.0
        if not np.allclose(w, np.round(w)):
            scale = 100.0  # scale to reduce fractional flows for non-integers
            w = np.round(w * scale).astype(int)
            total_w = int(w.sum())
            # Update capacities accordingly
            cap_lo = int(round(cap_lo * scale))
            cap_hi = int(round(cap_hi * scale))
            # Rebuild source/sink demands
            G.nodes[source]["demand"] = -float(total_w)
            G.nodes[sink]["demand"] = float(total_w)
            # Update source->item capacity
            for i in range(n):
                G[source][f"p_{i}"]["capacity"] = int(w[i])

        # Create edges p_i -> c_j
        for i in range(n):
            for j in range(k):
                # cost must be integer for some solvers; scale meters to decimeters to keep precision
                cost = int(round(D[i, j] * 10))
                G.add_edge(f"p_{i}", f"c_{j}", capacity=int(w[i]), weight=cost)

        # 4) Solve min cost flow
        flow = nx.min_cost_flow(G)  # requires networkx >= 2.x with a solver available

        # 5) Extract assignments (winner-take-most by flow)
        new_labels = np.empty(n, dtype=int)
        for i in range(n):
            flows = []
            for j in range(k):
                f = flow[f"p_{i}"].get(f"c_{j}", 0)
                flows.append(f)
            new_labels[i] = int(np.argmax(flows))

        # 6) Update centers as weighted means
        centers_new = np.zeros_like(centers)
        for j in range(k):
            mask = new_labels == j
            if mask.any():
                ww = w[mask]
                centers_new[j] = (X[mask] * ww[:, None]).sum(axis=0) / ww.sum()
            else:
                # empty cluster: re-seed at farthest point
                far_idx = np.argmax(np.min(dist_matrix(X, centers), axis=1))
                centers_new[j] = X[far_idx]

        # Check convergence
        if np.array_equal(new_labels, labels):
            labels = new_labels
            centers = centers_new
            break
        labels = new_labels
        centers = centers_new

    out = gdf.copy()
    out["cluster"] = labels

    centers_gdf = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy(centers[:, 0], centers[:, 1]), crs=gdf.crs
    )
    # Transform to WGS84 (lat/lon)
    gdf_wgs84 = centers_gdf.to_crs(4326)
    centers_latlon = np.column_stack(
        [
            gdf_wgs84.geometry.y.values,  # lat
            gdf_wgs84.geometry.x.values,  # lon
        ]
    )

    return (
        out,
        centers_latlon,
    )


def capacitated_kmeans_autodetect(
    df: pd.DataFrame,
    k: int,
    weight_col: str = "count",
    x_col: str = None,
    y_col: str = None,
    max_iter: int = 30,
    random_state: int = 42,
    initial_tolerance: float = 0.1,
    precision: float = 0.01,
    max_attempts: int = 20,
):
    """
    Automatically finds the optimal capacity tolerance using binary search.

    Args:
        df: Input DataFrame
        k: Number of clusters
        weight_col: Column name for weights
        x_col: Column name for x coordinates
        y_col: Column name for y coordinates
        max_iter: Maximum iterations for k-means
        random_state: Random seed
        initial_tolerance: Starting tolerance value
        precision: Desired precision (0.01 for 2 decimal places)
        max_attempts: Maximum number of attempts to find a solution

    Returns:
        Tuple of (out, centers, info) from capacitated_kmeans
    """
    low = 0.0
    high = 1.0
    best_tolerance = None
    best_result = None
    mid = None

    for attempt in range(max_attempts):
        old_mid = mid
        mid = (low + high) / 2
        mid = round(mid, 2)  # Round to 2 decimal places
        if mid == old_mid:
            break

        try:
            out, centers = capacitated_kmeans(
                df,
                k,
                weight_col,
                x_col,
                y_col,
                capacity_tolerance=mid,
                max_iter=max_iter,
                random_state=random_state,
            )
            logger.info(
                "Capacity tolerance found, decreasing tolerance", capacity_tolerance=mid
            )
            best_tolerance = mid
            best_result = (out, centers)

            # Try to find a lower tolerance that still works
            high = mid
        except nx.NetworkXUnfeasible:
            # Need to increase tolerance
            low = mid
            logger.info("Increasing tolerance", capacity_tolerance=mid)

        # Check if we've reached desired precision
        if (high - low) < precision:
            break

    if best_result is not None:
        logger.info(
            "Capacity tolerance found after",
            attempts=attempt,
            capacity_tolerance=best_tolerance,
        )
        return best_result

    raise Exception(
        f"Failed to find a valid capacity tolerance after {max_attempts} attempts"
    )
