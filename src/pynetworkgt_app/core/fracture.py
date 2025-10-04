"""Domain models representing fracture networks."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from shapely.geometry import LineString

try:  # pragma: no cover - import guard
    import geopandas as gpd
except ImportError:  # pragma: no cover
    gpd = None


@dataclass
class FractureLine:
    """Single fracture segment represented as a line."""

    geometry: LineString
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FractureNetwork:
    """Collection of fracture lines with optional metadata."""

    lines: Iterable[FractureLine]
    crs: Optional[str] = None
    source: Optional[Path] = None

    def __post_init__(self) -> None:
        self.lines = list(self.lines)

    def __len__(self) -> int:
        return len(self.lines)

    def total_length(self) -> float:
        """Return the cumulative length of all fractures."""

        return sum(line.geometry.length for line in self.lines)

    def to_geodataframe(self):
        """Convert the fracture network into a GeoDataFrame.

        Returns
        -------
        geopandas.GeoDataFrame
            Each fracture line becomes a GeoDataFrame row with its properties.

        Raises
        ------
        ImportError
            If geopandas is not installed in the current environment.
        """

        if gpd is None:  # pragma: no cover - executed without geopandas
            raise ImportError("geopandas is required to convert to GeoDataFrame")

        records: List[Dict[str, Any]] = []
        for line in self.lines:
            record = dict(line.properties)
            record["geometry"] = line.geometry
            records.append(record)

        return gpd.GeoDataFrame(records, geometry="geometry", crs=self.crs)

