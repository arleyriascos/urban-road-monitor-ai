"""Shape of GET /internal/graph, the road graph the backend sends."""

from pydantic import BaseModel, ConfigDict, Field
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


class GraphPayload(_BackendModel):
    version: str = Field(min_length=1, max_length=128)
    nodes: list[GraphNodeIn]
    segments: list[GraphSegmentIn]
