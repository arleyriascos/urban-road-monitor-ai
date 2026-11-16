"""Contract of POST /clusters: what the backend sends and what it gets back.

Field names travel in camelCase, like the rest of the project's APIs. Detection ids are
those of the database (detections), and segment ids those of road_segments.
"""

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.clustering.clusters import ClusterStatus
from app.clustering.models import Severity


class _ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, validate_by_name=True, validate_by_alias=True, frozen=True
    )


class DetectionIn(_ApiModel):
    """One time the camera saw a pothole, as the backend stored it."""

    model_config = ConfigDict(extra="forbid")

    id: int
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False, examples=[1.2136])
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False, examples=[-77.2811])
    severity: Severity
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False, examples=[0.82])
    detected_at: AwareDatetime = Field(description="When it was seen. It must carry a time zone.")


class ClusterRequest(_ApiModel):
    model_config = ConfigDict(extra="forbid")

    detections: list[DetectionIn]
    graph_version: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        description="Version of the road graph, to place each pothole on its street.",
    )
    as_of: AwareDatetime | None = Field(
        default=None, description="The moment the confidence is measured at. Default: now."
    )
    eps_m: float | None = Field(
        default=None,
        gt=0,
        le=1000,
        allow_inf_nan=False,
        description="Override of CLUSTER_EPS_M for this request.",
    )
    min_points: int | None = Field(
        default=None, ge=1, le=100, description="Override of CLUSTER_MIN_POINTS for this request."
    )


class ClusterOut(_ApiModel):
    """One pothole, built from the detections that point at it."""

    detection_ids: list[int]
    count: int
    latitude: float
    longitude: float
    severity: Severity
    confidence: float
    status: ClusterStatus
    segment_id: int | None = Field(description="Road segment the pothole is on, if one is near.")
    segment_distance_m: float | None
    segment_fraction: float | None = Field(
        description="Where along the segment: 0 at its start, 1 at its end."
    )
    first_detected_at: AwareDatetime
    last_detected_at: AwareDatetime


class ClusterResponse(_ApiModel):
    graph_version: str | None = Field(
        description="Version of the graph used to find the segments; null if none was used."
    )
    as_of: AwareDatetime
    eps_m: float
    min_points: int
    detection_count: int
    cluster_count: int
    confirmed_count: int
    placed_count: int = Field(description="Potholes that were put on a road segment.")
    computation_ms: int
    clusters: list[ClusterOut]
