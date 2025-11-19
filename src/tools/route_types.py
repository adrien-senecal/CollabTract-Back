import re
from pydantic import BaseModel, Field, field_validator, ValidationInfo


class MapRequest(BaseModel):
    city_name: str
    department_code: int | str
    cluster_count: int = Field(1, ge=1)
    clustering_method: str = "kmeans"
    cluster_colors: list[str] | None = None
    seed: int = 42
    cluster_id: int | None = None

    @field_validator("clustering_method")
    def validate_clustering_method(cls, v):
        allowed = {"kmeans", "balanced_length", "balanced_count"}
        if v not in allowed:
            raise ValueError(f"clustering_method must be one of: {allowed}")
        return v

    @field_validator("cluster_id")
    def validate_cluster_id(cls, v, info: ValidationInfo):
        if v is not None and v < 0:
            raise ValueError("cluster_id must be a non-negative integer")

        cluster_count = info.data.get("cluster_count")
        if cluster_count is not None and v is not None and v >= cluster_count:
            raise ValueError("cluster_id must be less than cluster_count")
        return v


class RouteConfig(BaseModel):
    name: str
    color: str | None = None

    @field_validator("color")
    def validate_color(cls, v):
        if v and not re.match(r"^#([0-9a-fA-F]{6})$", v):
            raise ValueError("Invalid hex color")
        return v


class RouteListConfig(BaseModel):
    route_count: int = 1
    routes: list[RouteConfig] = Field(default_factory=list)
    random_state: int = 42
    clustering_method: str = "kmeans"
    seed: int = 42

    @field_validator("clustering_method")
    def validate_clustering_method(cls, v):
        allowed = {"kmeans", "balanced_length", "balanced_count"}
        if v not in allowed:
            raise ValueError(f"clustering_method must be one of: {allowed}")
        return v
