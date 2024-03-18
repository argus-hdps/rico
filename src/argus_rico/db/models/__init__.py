__all__ = [
    "Telescope",
    "TelescopeModel",
    "Camera",
    "CameraModel",
    "Throughput",
    "SpectralThroughput",
    "Focuser",
    "FilterModel",
    "Instrument",
    "OcularUnit",
    "BoltwoodReport",
    "PathfinderHVAC",
]

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata

from .climate import BoltwoodReport, PathfinderHVAC  # noqa: E402
from .hardware import (  # noqa: E402
    Camera,
    CameraModel,
    FilterModel,
    Focuser,
    Instrument,
    OcularUnit,
    SpectralThroughput,
    Telescope,
    TelescopeModel,
    Throughput,
)
