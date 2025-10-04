"""Utilities for reading and writing fracture networks from GeoPackage files."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Union

from shapely.geometry.base import BaseGeometry

from ..core.fracture import FractureLine, FractureNetwork

try:  # pragma: no cover - import guard
    import geopandas as gpd
except ImportError as exc:  # pragma: no cover - runtime dependency
    gpd = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


class FractureGpkgError(RuntimeError):
    """Raised when a GeoPackage fracture layer cannot be parsed."""


SUPPORTED_GEOMETRIES = {"LineString", "MultiLineString"}


def read_fracture_gpkg(
    path: Union[str, Path],
    *,
    layer: Optional[str] = None,
    include_attributes: bool = True,
    explode_multilines: bool = True,
) -> FractureNetwork:
    """Read a GeoPackage layer into a :class:`FractureNetwork`.

    Parameters
    ----------
    path:
        Path to the GeoPackage file.
    layer:
        Name of the layer to load. When ``None`` (default) the first layer is used.
    include_attributes:
        When ``True`` (default) store feature attributes in ``FractureLine.properties``.
    explode_multilines:
        When ``True`` (default) split ``MultiLineString`` geometries into individual
        ``FractureLine`` records. Otherwise keep them as a single entry.
    """

    if gpd is None:  # pragma: no cover - executed when geopandas missing
        raise FractureGpkgError(
            "geopandas is required to read GeoPackage files"
        ) from _IMPORT_ERROR

    file_path = Path(path)
    if not file_path.exists():
        raise FractureGpkgError(f"GeoPackage file not found: {file_path}")

    try:
        gdf = gpd.read_file(file_path, layer=layer)
    except Exception as exc:  # pragma: no cover - geopandas handles errors
        raise FractureGpkgError(f"Failed to read GeoPackage: {exc}") from exc

    if gdf.empty:
        raise FractureGpkgError("Layer contains no features")

    lines: List[FractureLine] = []
    for _, row in gdf.iterrows():
        geometry: BaseGeometry = row.geometry
        if geometry is None or geometry.is_empty:
            continue
        geom_type = geometry.geom_type
        if geom_type not in SUPPORTED_GEOMETRIES:
            raise FractureGpkgError(
                f"Unsupported geometry type '{geom_type}'. Only lines are allowed."
            )

        attrs = _extract_attributes(row, include_attributes)

        if geom_type == "LineString" or not explode_multilines:
            lines.append(FractureLine(geometry=geometry, properties=attrs))
        else:
            for part in geometry.geoms:  # type: ignore[attr-defined]
                lines.append(FractureLine(geometry=part, properties=attrs.copy()))

    if not lines:
        raise FractureGpkgError("No valid line geometries were found in the layer")

    crs = gdf.crs.to_wkt() if gdf.crs else None
    return FractureNetwork(lines=lines, crs=crs, source=file_path)


def write_fracture_gpkg(
    network: FractureNetwork,
    path: Union[str, Path],
    *,
    layer: str = "fractures",
    driver: str = "GPKG",
    overwrite: bool = True,
) -> Path:
    """Write a :class:`FractureNetwork` to a GeoPackage layer."""

    if gpd is None:  # pragma: no cover
        raise FractureGpkgError(
            "geopandas is required to write GeoPackage files"
        ) from _IMPORT_ERROR

    file_path = Path(path)
    if file_path.parent and not file_path.parent.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)

    gdf = network.to_geodataframe()

    if overwrite and file_path.exists():
        file_path.unlink()

    try:
        gdf.to_file(file_path, layer=layer, driver=driver)
    except Exception as exc:
        raise FractureGpkgError(f"Failed to write GeoPackage: {exc}") from exc

    return file_path


def _extract_attributes(row, include: bool) -> dict:
    if not include:
        return {}

    attrs = row.to_dict()
    attrs.pop("geometry", None)
    return attrs


__all__ = [
    "read_fracture_gpkg",
    "write_fracture_gpkg",
    "FractureGpkgError",
]

