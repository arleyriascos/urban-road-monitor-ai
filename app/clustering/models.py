"""What goes into the clustering and what comes out of it."""

import math
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ClusteringError(ValueError):
    """Raised when a setting or a detection cannot be clustered."""


class Severity(StrEnum):
    """How bad a pothole looks, from the share of the picture its box covers."""

    LEVE = "leve"
    MODERADO = "moderado"
    GRAVE = "grave"

    @property
    def rank(self) -> int:
        """0 for leve, 1 for moderado, 2 for grave: a higher rank is worse."""
        return _RANKS[self]


_RANKS = {Severity.LEVE: 0, Severity.MODERADO: 1, Severity.GRAVE: 2}


@dataclass(frozen=True, slots=True)
class Detection:
    """One time the camera saw a pothole."""

    id: int
    latitude: float
    longitude: float
    severity: Severity
    confidence: float
    """How sure the vision model was, from 0 to 1."""
    detected_at: datetime
    """When it was seen. It must carry a time zone."""

    def __post_init__(self) -> None:
        if not (math.isfinite(self.latitude) and -90.0 <= self.latitude <= 90.0):
            raise ClusteringError(f"detection {self.id}: latitude out of range: {self.latitude}")
        if not (math.isfinite(self.longitude) and -180.0 <= self.longitude <= 180.0):
            raise ClusteringError(f"detection {self.id}: longitude out of range: {self.longitude}")
        if not (math.isfinite(self.confidence) and 0.0 <= self.confidence <= 1.0):
            raise ClusteringError(f"detection {self.id}: confidence not in 0..1: {self.confidence}")
        if self.detected_at.tzinfo is None:
            raise ClusteringError(f"detection {self.id}: detected_at must carry a time zone")
