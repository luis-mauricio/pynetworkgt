"""Digitising helpers to convert binary rasters into fracture networks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Set, Tuple

import numpy as np

try:  # pragma: no cover
    import networkx as nx
except ImportError as exc:  # pragma: no cover
    raise RuntimeError('networkx is required for fracture digitising') from exc
from shapely.geometry import LineString

try:  # pragma: no cover - optional dependency for file IO
    import rasterio
except ImportError:  # pragma: no cover
    rasterio = None

from skimage.morphology import skeletonize

from ...core.fracture import FractureLine, FractureNetwork


@dataclass
class DigitiseOptions:
    """Configuration options for fracture digitising."""

    invert: bool = False
    simplify_tolerance: float = 0.0
    min_branch_length: float = 0.0


def _normalise_transform(transform: Optional[Sequence[float]]) -> Tuple[float, float, float, float, float, float]:
    if transform is None:
        return (1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    if hasattr(transform, "a") and hasattr(transform, "b"):
        return (float(transform.a), float(transform.b), float(transform.c), float(transform.d), float(transform.e), float(transform.f))
    if isinstance(transform, (tuple, list)) and len(transform) == 6:
        return tuple(float(v) for v in transform)  # type: ignore[return-value]
    raise TypeError('transform must be a 6-tuple or affine-like object')


def digitise_fracture_network(
    array: np.ndarray,
    *,
    transform: Optional[Sequence[float]] = None,
    options: Optional[DigitiseOptions] = None,
) -> FractureNetwork:
    """Convert a binary fracture mask into a :class:`FractureNetwork`.

    Parameters
    ----------
    array:
        2D binary array (``True`` / ``1`` = fracture signal).
    transform:
        Transform mapping pixel centres to map coordinates. Accepts objects
        exposing ``a, b, c, d, e, f`` attributes (e.g. affine matrices) or a 6-tuple
        ``(a, b, c, d, e, f)``.
        Defaults to unit spacing with origin at (0, 0).
    options:
        Digitising options controlling inversion, simplification, and clean-up.
    """

    if array.ndim != 2:
        raise ValueError("Input array must be 2-dimensional")

    options = options or DigitiseOptions()
    mask = _prepare_mask(array, invert=options.invert)

    skeleton = skeletonize(mask)
    graph = _skeleton_to_graph(skeleton)
    if graph.number_of_edges() == 0:
        return FractureNetwork(lines=[], crs=None, source=None)

    if nx is None:
        raise RuntimeError('networkx is required for fracture digitising')
    matrix = _normalise_transform(transform)
    lines = _graph_to_lines(graph, matrix)

    if options.simplify_tolerance > 0:
        simplified_lines = []
        for line in lines:
            simplified_lines.append(line.simplify(options.simplify_tolerance, preserve_topology=False))
        lines = simplified_lines

    if options.min_branch_length > 0:
        lines = [line for line in lines if line.length >= options.min_branch_length]
    else:
        lines = [line for line in lines if line.length > 0]

    fracture_lines = [FractureLine(geometry=line) for line in lines]
    return FractureNetwork(lines=fracture_lines)


def digitise_fracture_network_from_raster(
    path: Path,
    *,
    band: int = 1,
    options: Optional[DigitiseOptions] = None,
) -> FractureNetwork:
    """Digitise a fracture network from a raster file (requires ``rasterio``)."""

    if rasterio is None:  # pragma: no cover - runtime guard
        raise RuntimeError("rasterio is required to digitise from raster files")

    with rasterio.open(path) as dataset:
        array = dataset.read(band)
        transform = _normalise_transform(dataset.transform)
    return digitise_fracture_network(array, transform=transform, options=options)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

NEIGHBOURS = np.array(
    [
        (-1, 0),
        (0, -1),         (0, 1),
        (1, 0),
    ]
)


def _apply_transform(matrix: Tuple[float, float, float, float, float, float], col: float, row: float) -> Tuple[float, float]:
    a, b, c, d, e, f = matrix
    x = a * col + b * row + c
    y = d * col + e * row + f
    return float(x), float(y)


def _prepare_mask(array: np.ndarray, *, invert: bool) -> np.ndarray:
    mask = np.asarray(array)
    if mask.dtype != np.bool_:
        mask = mask > 0
    if invert:
        mask = ~mask
    return mask


def _skeleton_to_graph(mask: np.ndarray) -> nx.Graph:
    rows, cols = np.nonzero(mask)
    graph: nx.Graph = nx.Graph()
    for r, c in zip(rows, cols):
        node = (int(r), int(c))
        graph.add_node(node)

    for r, c in zip(rows, cols):
        node = (int(r), int(c))
        for dr, dc in NEIGHBOURS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < mask.shape[0] and 0 <= nc < mask.shape[1]:
                if mask[nr, nc]:
                    neighbour = (int(nr), int(nc))
                    if node != neighbour:
                        weight = float(np.hypot(dr, dc))
                        graph.add_edge(node, neighbour, weight=weight)
    return graph


def _graph_to_lines(graph: nx.Graph, transform: Tuple[float, float, float, float, float, float]) -> List[LineString]:
    visited: Set[frozenset] = set()
    lines: List[LineString] = []

    significant_nodes = [n for n in graph.nodes if graph.degree(n) != 2]
    for node in significant_nodes:
        for nbr in graph.neighbors(node):
            edge = frozenset((node, nbr))
            if edge in visited:
                continue
            path = _walk_path(graph, node, nbr, visited)
            line = _path_to_linestring(path, transform)
            if line is not None:
                lines.append(line)

    for node in graph.nodes:
        for nbr in graph.neighbors(node):
            edge = frozenset((node, nbr))
            if edge in visited:
                continue
            path = _walk_cycle(graph, node, nbr, visited)
            line = _path_to_linestring(path, transform, closed=True)
            if line is not None:
                lines.append(line)
    return lines


def _walk_path(
    graph: nx.Graph,
    start: Tuple[int, int],
    neighbour: Tuple[int, int],
    visited: Set[frozenset],
) -> List[Tuple[int, int]]:
    path = [start]
    current = neighbour
    previous = start
    visited.add(frozenset((start, neighbour)))

    while True:
        path.append(current)
        neighbours = [n for n in graph.neighbors(current) if n != previous]
        if len(neighbours) != 1 or graph.degree(current) != 2:
            break
        next_node = neighbours[0]
        visited.add(frozenset((current, next_node)))
        previous, current = current, next_node
    return path


def _walk_cycle(
    graph: nx.Graph,
    start: Tuple[int, int],
    neighbour: Tuple[int, int],
    visited: Set[frozenset],
) -> List[Tuple[int, int]]:
    path = [start]
    current = neighbour
    previous = start
    visited.add(frozenset((start, neighbour)))

    while current != start:
        path.append(current)
        neighbours = [n for n in graph.neighbors(current) if n != previous]
        if not neighbours:
            break
        next_node = neighbours[0]
        edge = frozenset((current, next_node))
        if edge in visited:
            break
        visited.add(edge)
        previous, current = current, next_node
    if path[-1] != start:
        path.append(start)
    return path


def _path_to_linestring(
    path: Iterable[Tuple[int, int]],
    transform: Tuple[float, float, float, float, float, float],
    *,
    closed: bool = False,
) -> Optional[LineString]:
    coords: List[Tuple[float, float]] = []
    for r, c in path:
        x, y = _apply_transform(transform, c + 0.5, r + 0.5)
        coords.append((x, y))
    if len(coords) < 2:
        return None
    if closed and coords[0] != coords[-1]:
        coords.append(coords[0])
    line = LineString(coords)
    if line.is_empty or line.length == 0:
        return None
    return line

