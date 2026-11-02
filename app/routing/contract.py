"""Contract of POST /routes: what the backend sends and what it gets back.

Field names travel in camelCase (graphVersion), like the rest of the project's APIs.
Ids are those of the database (road_nodes, road_segments), never internal indexes.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

Algorithm = Literal["astar", "dijkstra"]
"""The same names the database uses (route_requests.algorithm)."""


class _ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, validate_by_name=True, validate_by_alias=True, frozen=True
    )


class Point(_ApiModel):
    model_config = ConfigDict(extra="forbid")

    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False, examples=[1.2136])
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False, examples=[-77.2811])


class RouteRequest(_ApiModel):
    model_config = ConfigDict(extra="forbid")

    origin: Point
    destination: Point
    k: float = Field(
        default=1.0,
        ge=0,
        allow_inf_nan=False,
        description="Damage factor: cost = length x (1 + k x damage).",
    )
    graph_version: str = Field(
        min_length=1,
        max_length=128,
        description="Version of the road graph the backend computed.",
        examples=["940ab0350236d4a94de0b11d6ed78931"],
    )
    algorithm: Algorithm = "astar"


class SnappedPoint(_ApiModel):
    """The intersection a clicked point was moved to, and how far it was."""

    node_id: int
    latitude: float
    longitude: float
    distance_m: float


class RouteStepOut(_ApiModel):
    segment_id: int
    reversed: bool = Field(description="True if the segment is crossed against its geometry.")
    length_m: float
    damage_score: float
    cost: float


class RouteResponse(_ApiModel):
    algorithm: Algorithm
    graph_version: str = Field(description="Version of the graph actually used.")
    origin: SnappedPoint
    destination: SnappedPoint
    total_length_m: float
    total_cost: float
    explored_nodes: int
    computation_ms: int = Field(description="Time of the search only, without loading the graph.")
    node_ids: list[int]
    steps: list[RouteStepOut]


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """Shape of every error, the same as the backend's."""

    error: ErrorDetail
