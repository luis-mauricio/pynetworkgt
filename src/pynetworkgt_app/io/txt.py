"""Utilities for reading and writing fracture networks in the bespoke TXT format."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple, Union

from shapely.geometry import LineString

from ..core.fracture import FractureLine, FractureNetwork


class FractureTxtError(RuntimeError):
    """Raised when the TXT fracture file cannot be parsed."""


def read_fracture_txt(
    path: Union[str, Path],
    *,
    delimiter: Optional[str] = None,
    skip_empty: bool = True,
    comment_prefix: str = "#",
) -> FractureNetwork:
    """Read a TXT fracture network file and return a :class:`FractureNetwork`.

    Parameters
    ----------
    path:
        File system path to the TXT file.
    delimiter:
        Explicit delimiter between coordinate values. Defaults to ``None``,
        which means any consecutive whitespace is treated as a separator.
    skip_empty:
        When ``True`` (default), blank lines are ignored. Otherwise a blank
        line triggers :class:`FractureTxtError`.
    comment_prefix:
        Lines starting with this prefix are ignored. Defaults to ``#``.

    Returns
    -------
    FractureNetwork
        Parsed fracture lines and associated metadata.
    """

    file_path = Path(path)
    if not file_path.exists():
        raise FractureTxtError(f"Fracture file not found: {file_path}")

    lines: List[FractureLine] = []
    raw_lines = file_path.read_text(encoding="utf-8").splitlines()

    for index, raw_line in enumerate(raw_lines, start=1):
        entry = raw_line.strip()
        if not entry:
            if skip_empty:
                continue
            raise FractureTxtError(f"Blank line at {index} in {file_path}")
        if entry.startswith(comment_prefix):
            continue

        try:
            coordinates = _parse_coordinate_sequence(entry, delimiter)
        except ValueError as exc:
            raise FractureTxtError(
                f"Invalid numeric values on line {index}: {exc}" 
            ) from exc
        except FractureTxtError as exc:
            raise FractureTxtError(f"Line {index}: {exc}") from exc

        line_geometry = LineString(coordinates)
        if line_geometry.is_empty:
            raise FractureTxtError(f"Line {index} resulted in an empty geometry")

        lines.append(FractureLine(geometry=line_geometry))

    if not lines:
        raise FractureTxtError(f"No fracture geometries found in {file_path}")

    return FractureNetwork(lines=lines, source=file_path)


def write_fracture_txt(
    network: FractureNetwork,
    path: Union[str, Path],
    *,
    delimiter: str = "\t",
    include_comments: bool = True,
) -> Path:
    """Write a :class:`FractureNetwork` to the bespoke TXT format.

    Parameters
    ----------
    network:
        Fracture network to serialise.
    path:
        Destination path. Parent directories are created automatically.
    delimiter:
        Character used to separate coordinate values. Defaults to tab.
    include_comments:
        When ``True`` a short header comment with CRS/source metadata is added.
    """

    file_path = Path(path)
    if file_path.parent and not file_path.parent.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)

    lines: List[str] = []
    if include_comments:
        if network.crs:
            lines.append(f"# CRS: {network.crs}")
        if network.source:
            lines.append(f"# Source: {network.source}")

    for fracture in network.lines:
        coords = [f"{coord:.12g}" for point in fracture.geometry.coords for coord in point]
        lines.append(delimiter.join(coords))

    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return file_path


def _parse_coordinate_sequence(
    text: str, delimiter: Optional[str]
) -> List[Tuple[float, float]]:
    """Convert a whitespace or delimiter separated string into coordinates."""

    raw_values = text.split(delimiter) if delimiter is not None else text.split()
    if len(raw_values) % 2 != 0:
        raise FractureTxtError("Coordinate list must contain an even number of values")

    values: List[float] = [float(value) for value in raw_values]
    coordinates: List[Tuple[float, float]] = []

    for index in range(0, len(values), 2):
        x = values[index]
        y = values[index + 1]
        coordinates.append((x, y))

    if len(coordinates) < 2:
        raise FractureTxtError("Each fracture line must contain at least two points")

    return coordinates


__all__ = ["read_fracture_txt", "write_fracture_txt", "FractureTxtError"]

