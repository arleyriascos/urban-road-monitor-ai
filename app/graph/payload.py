"""Shape of GET /internal/graph, the road graph the backend sends."""

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


class _BackendModel(BaseModel):
    """Fields arrive in camelCase (fromNodeId); in Python they are snake_case."""

    model_config = ConfigDict(
        alias_generator=to_camel, validate_by_name=True, validate_by_alias=True, frozen=True
    )


class GraphNodeIn(_BackendModel):
    id: int
    latitude: float
    longitude: float


class GraphSegmentIn(_BackendModel):
    id: int
    from_node_id: int
    to_node_id: int
    length_m: float
    damage_score: float
    is_oneway: bool
    geometry: list[tuple[float, float]] | None = Field(default=None, max_length=2000)
    """The shape of the street as (latitude, longitude) pairs, from its start to its end.

    Optional: a backend that does not send it gets a straight line between the two nodes.
    """

    @field_validator("geometry")
    @classmethod
    def _check_geometry(
        cls, geometry: list[tuple[float, float]] | None
    ) -> list[tuple[float, float]] | None:
        if geometry is None:
            return None
        if len(geometry) < 2:
            raise ValueError("geometry needs at least two points")
        for latitude, longitude in geometry:
            if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
                raise ValueError(f"geometry point out of range: ({latitude}, {longitude})")
        return geometry


class GraphPayload(_BackendModel):
    version: str = Field(min_length=1, max_length=128)
    nodes: list[GraphNodeIn]
    segments: list[GraphSegmentIn]
